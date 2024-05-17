#  Tree of Clarifications (ToC)

Original Repository:
[tree-of-clarications](https://github.com/gankim/tree-of-clarifications)

Original EMNLP 2023 paper:
[Tree of Clarifications: Answering Ambiguous Questions with Retrieval-Augmented Large Language Models](https://arxiv.org/abs/2310.14696)


## Summary
We apply the framework, <b>Tree of Clarifications (ToC)</b> proposed in the [EMNLP 2023 paper](https://arxiv.org/abs/2310.14696) fro answering ambiguous questions to answering complex multi-hop question combined with retrieval-augmented generation.

## Preparing the Dataset
- The Complex Web Questions dataset can be downloaded from [here](https://www.tau-nlp.sites.tau.ac.il/compwebq).
- The ASQA dataset is [here](https://github.com/google-research/language/tree/master/language/asqa). We have utilized the pre-packaged version from the original repository.

## Answering multi-hop questions with ToC
Before running ToC, you need to specify the following. Fill openAI API key by referring to the [homepage](https://openai.com/). We utilized the server hosted by [DSPy](https://github.com/stanfordnlp/dspy). 

To run ToC, use the following script, specifying the necessary paths and options:

```
python run_toc.py --openai_key $OPENAI_KEY --output_dir $OUT_DIR ${ARGS}
```
### Required Arguments
- openai_key: Your OpenAI Key
- output_dir: Directory where output files should be stored

## Reference
```
@article{kim2023tree,
  title={Tree of Clarifications: Answering Ambiguous Questions with Retrieval-Augmented Large Language Models},
  author={Gangwoo Kim and Sungdong Kim and Byeongguk Jeon and Joonsuk Park and Jaewoo Kang},
  journal={EMNLP},
  year={2023}
}
```
