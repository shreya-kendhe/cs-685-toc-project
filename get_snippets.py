import json

def get_snippets(qid):
    f_snippet = open("complexwebquestions_V1_1/web_snippets_dev.json/web_snippets_dev.json")
    data_snippet = json.load(f_snippet)
    for i in data_snippet:
        if i["question_ID"] == qid:
            snippets = []
            for j in i["web_snippets"]:
                snippets.append(j["snippet"])
            return snippets
    return []
