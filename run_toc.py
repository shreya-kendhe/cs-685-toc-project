import os
import json
import dsp
import argparse
from tqdm import tqdm
from get_snippets import get_snippets

from toc import (
    rerank,
    parse_disambig, make_str_disambig,
    ToC, Node,
    get_rac_template,
    check_unique, verify_with_evidence,
)
from utils import save_results


def get_dataset():
    data_path = os.path.join("complexwebquestions_V1_1/ComplexWebQuestions_dev.json")
    data = json.load(open(data_path))
    qa_pairs = []
    for ins in data:
        question = ins['question']
        answers = [anns['answer'] for anns in ins['answers']]

        entry = {'question' : question,
                 'answer'   : answers,
                 'id'       : ins['ID'],
        }
        qa_pairs += [entry]
    examples = [dsp.Example(**kw_example) for kw_example in qa_pairs]
    return examples, data

def get_dataset_ASQA():
    data_path = os.path.join("asqa/ASQA.json")
    data = json.load(open(data_path))
    qa_pairs = {}
    qa_pairs["train"] = []
    for idx, (id, ins) in enumerate(data["train"].items()):
        question = ins['ambiguous_question']
        answers = [anns['long_answer'] for anns in ins['annotations']]

        entry = {'question' : question,
                 'answer'   : answers,
                 'id'       : id,
        }

        str_disambigs = make_str_disambig(ins['qa_pairs'])
        entry.update({'disambig' : str_disambigs})

        qa_pairs["train"] += [entry]

    train = [dsp.Example(**kw_example) for kw_example in qa_pairs['train']]
    return train, data


def get_example(args, train, ins, passages,
                reranker=None, consolidation=False):
    question = ins.question
    with dsp.settings.context(vectorizer=dsp.SentenceTransformersVectorizer()):
        knn_func = dsp.knn(train)
        n_dynamic = args.n_shot
        
        #given current question and number of shots n returns most relevant demos using sentencebert
        demos = knn_func(ins, n_dynamic)
        demos.reverse()

    dic_example = {'question': question,
                   'demos': demos,
                   }

    #Ranks top-k passages from all the passages for the current ambig-dict and attaches them to the context
    if args.top_k_reranked > 0 and reranker is not None: # when using reranker
        top_k_reranked = min(args.top_k_reranked, len(passages))
        passages = rerank(reranker, question, passages, top_k_reranked)
        dic_example.update({'context' : passages})

    if consolidation:
        dic_example.update({'disambig' : ins.disambig})

    example = dsp.Example(**dic_example)

    return example

#Prompts the LLM according to the template, returns answer and completions
@dsp.transformation
def QD_predict(example: dsp.Example, qd_template,
               sc=False, temperature=0.0):
    example, completions = dsp.generate(qd_template, temperature=temperature)(example, stage='qa')

    kw_out = {
            'answer': completions.answer,
            'disambig': completions.disambig,
    }

    out_example = example.copy(**kw_out)

    return out_example, completions

def remove_demos(demos, target_ids):
    new_demos = []
    for demo in demos:
        if demo.id not in target_ids:
            new_demos += [demo]
    return new_demos

def remove_dup_demos(demos, lst_disambigs):
    answers = []
    for disambig in lst_disambigs:
        answers += [disambig['answer']]

    target_ids = []
    for demo in demos:
        demo_disambigs = parse_disambig(demo.disambig)
        for da in demo_disambigs:
            if dsp.metrics.F1(da['answer'], answers) > 0.8:
                target_ids += [demo.id]

    demos = remove_demos(demos, target_ids)

    return demos

def remove_dup_psgs(passages, contexts, lst_disambigs):
    answers = []
    for disambig in lst_disambigs:
        answers += [disambig['answer']]

    target_idxs = []
    for idx, passage in enumerate(passages):
        if passage in contexts and \
            dsp.passage_has_answers(passage, answers):
                target_idxs += [idx]

    passages = [passage for idx, passage in enumerate(passages) if idx not in target_idxs]

    return passages

def get_argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default='', type=str, help="The prefix of output files.")
    parser.add_argument("--model_type", default='davinci-002', type=str, help="The GPT model type.")
    parser.add_argument("--openai_key",  default="", type=str, required=False, help="The openai key.")
    parser.add_argument("--temperature", default=0.7, type=float, help="The temperature for generation.")
    parser.add_argument("--n_shot", default=3, type=int, help="The number of few-shot examples for in-context learning.")
    parser.add_argument("--n_dev", default=20, type=int, help="The number of dev examples to run.")
    parser.add_argument("--max_nodes", default=5, type=int, help="The maximum number of nodes in a tree.")
    parser.add_argument("--max_depth", default=3, type=int, help="The maximum depth of a tree.")
    parser.add_argument("--max_trials", default=3, type=int, help="The maximum number of restarts.")
    parser.add_argument("--top_k_docs", default=100, type=int, help="The maximum number of retrieved documents.")
    parser.add_argument("--top_k_reranked", default=5, type=int, help="The maximum number of reranked documents.")
    parser.add_argument("--save_steps", default="1,5,10,15,20", type=str, help="you can save intermediate results.")
    parser.add_argument("--verify", default=True, action='store_true',)
    parser.add_argument(
        "--output_dir",
        default="",
        type=str,
        required=True,
        help="The output directory where predictions will be written.",
    )
    return parser

def main():
    parser = get_argparser()
    args = parser.parse_args()

    lm = dsp.GPT3(model=args.model_type, api_key=args.openai_key)
    kw_config = {'lm' : lm}

    if args.top_k_reranked > 0:
        kw_config['reranker'] = dsp.SentenceTransformersCrossEncoder()

    dsp.settings.configure(**kw_config)

    dev, data = get_dataset()
    train, _ = get_dataset_ASQA()
    rac_template = get_rac_template()

    kw_args_ex = {}
    if args.top_k_reranked > 0:
        kw_args_ex['reranker'] = dsp.settings.reranker

    if args.n_dev < 0:
        n_dev = len(dev)
    else:
        n_dev = min(args.n_dev, len(dev))

    os.makedirs(args.output_dir, exist_ok=True)
    save_steps = [int(save_step) for save_step in args.save_steps.split(",")] if args.save_steps != "" else []

    preds = [] ; outputs = []
    lst_err = []
 
    #looping over dev
    for idx, ambig_ins in enumerate(tqdm(dev[:n_dev])):
        #cur_demos will have the train set from ASQA
        print("\n", ambig_ins["question"])
        cur_demos = train.copy()
        if (idx + 1) % 10 == 0:
            print(f"{str(idx +1)} steps")

        #retrieve relevant passages to the current dict in ambig_ins from dataset
        all_passages = get_snippets(ambig_ins["id"])
        cur_passages = all_passages.copy() 
    
        #create root node of the first root ambig dict
        toc = ToC(root=Node(ambig_ins))

        #set pruning to True if verification is enabled
        do_pruning = args.verify == True
        n_restarts = 0 ; n_expansions = 0

        kw_args_ex.update({'consolidation': False})

        #while tree limits have not exceeded
        while n_restarts < args.max_trials and \
            toc.n_nodes < args.max_nodes and \
            n_expansions <= 15:

            n_expansions += 1
            if toc.leaf_nodes == []:
                toc.leaf_nodes = [toc.root]
                toc.leaf_nodes += toc.valid_nodes
                n_restarts += 1

            cur_node = toc.leaf_nodes.pop(0)
            #get the dict of the current node
            cur_ins = cur_node.ins
            if cur_node.depth > args.max_depth:
                continue

            #get n examples and context from the training set relevant to the current ambig dict in the current node
            qd_example = get_example(args, cur_demos, cur_ins, cur_passages, **kw_args_ex)
            
            #adds the context for the current question to slt_psgs.
            #slt_psgs is part of each node in the tree representing the context for that node.
            toc.slt_psgs += qd_example.context

            #gets the results from the LLM of disambig questions and answers, not sure what is stored in what
            qd_result, qd_completions = QD_predict(qd_example, rac_template, sc=False, temperature=args.temperature)
            try:
                #Try parsing the q/a pairs
                lst_disambigs = parse_disambig(qd_result.disambig)
                if lst_disambigs == []:
                    lst_disambigs = parse_disambig(qd_result.answer.split("\nAnswer:")[0])
            except:
                lst_err += [[idx, toc, qd_result.disambig]]

            if args.verify and len(lst_disambigs):
                cur_demos = remove_dup_demos(cur_demos, lst_disambigs)
                cur_passages = remove_dup_psgs(cur_passages, qd_example.context, lst_disambigs)

                if do_pruning:
                    valid_disambigs = []
                    for disambig in lst_disambigs:
                        if check_unique(toc.valid_qas, disambig):
                            ver_completion = verify_with_evidence(dsp.settings.lm,
                                                                toc,
                                                                disambig,
                                                                dsp.settings.reranker)
                            if "True" in ver_completion[0]:
                                valid_disambigs += [disambig]
                    lst_disambigs = valid_disambigs.copy()

            if len(lst_disambigs) > 0:
                toc.add_nodes(lst_disambigs, depth=cur_node.depth+1)
                continue

            if do_pruning:
                if n_restarts >= args.max_trials or n_expansions >= 10:
                    n_restarts = 0
                    do_pruning = False
                    continue

        tree_ins = toc._get_tree(args.max_nodes)

        kw_args_ex.update({'consolidation': True})
        ac_example = get_example(args, cur_demos, tree_ins, all_passages, **kw_args_ex)

        ac_result, ac_completions = QD_predict(ac_example, rac_template, sc=False)

        preds   += [ac_result.answer]
        outputs += [{"output": ac_completions.data[0], "stats":[{"nodes": toc.n_nodes, "depth": toc.leaf_depth}]}]

        if (idx + 1) in save_steps:
            with open(os.path.join(args.output_dir, f"output_{str(idx+1)}.json"), 'w') as f:
                json.dump(outputs, f, indent=4)
            print(f"Saved output_{idx}.json!")

    lm.inspect_history(n=1)

    save_results(args, data, preds, outputs)

if __name__ == "__main__":
    main()
