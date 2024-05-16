import dsp

def get_rac_template():
    instructions = " ".join([ 
        "I will provide complex questions whose answers require multi-hop reasoning.",
        "Clarify the given question into several sub-questions or disambiguated questions and provide short factoid answers to each question.",
        "Subsequently, aggregate them into a the final answer that answers the main question.",
        "Here are some examples."
    ])
    desc_disambig = "${the disambiguated pairs of questions and answers, each is separated by a new line.}"
    desc_subq = "SQ i: ${(i)-th disambiguated question that clarifies the ambiguous question}"
    desc_suba = "SA i: ${short factoid answers separated by semi-colon (;) to (i)-th disambiguated question, often between 1 and 5 words}"
    desc_answer = "${a thorough, detailed answer that explains the multiple interpretations of the original question and includes the appropriate disambiguations, at least three sentences.}"
    
    Context = dsp.Type(
        prefix="Context:\n",
        desc="${sources that may contain relevant content}",
        format=dsp.passages2text
    )
    
    AmbigQuestion = dsp.Type(prefix="Question:", desc="${ambiguous question to be disambiguated}")
    
    Disambiguations = dsp.Type(prefix="Subquestions:\n", 
                            desc="\n".join([desc_disambig, desc_subq, desc_suba]))
    
    Answer = dsp.Type(prefix="Answer:", desc=desc_answer, format=dsp.format_answers)

    dic_instruct = {'instructions': instructions}
    dic_instruct.update({'context': Context()})
    dic_instruct.update({'question': AmbigQuestion()})
    dic_instruct.update({'subques': Disambiguations()})
    dic_instruct.update({'answer': Answer()})
    
    rac_template = dsp.Template(**dic_instruct)
    
    return rac_template


def get_ver_prompt(evidence, orig_question, cur_qa):
    
    instruction = "I will provide a question, relevant context, and proposed answer to it. Identify whether the proposed answer could be correct or not with only 'True' or 'False'"
    
    prompt = instruction + "\n" + \
        "Context: " + evidence + "\n" + \
        "Question: " + orig_question + "\n" + \
        "Proposed Answer: " + cur_qa['answer']
        
    return prompt