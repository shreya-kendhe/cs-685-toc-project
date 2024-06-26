import numpy as np
import dsp

#Retrieves passages relevant to the current question in dev from colbert and return top-k
def retrieve(query: str, k: int) -> list[str]:
    """Retrieves passages from the RM for the query and returns the top k passages."""
    if not dsp.settings.rm:
        raise AssertionError("No RM is loaded.")
    #Call to ColBert returns a dict probably relevant to the passages, next step creates a list of the "long_text"
    passages = dsp.settings.rm(query, k=k)
    passages = [psg.long_text for psg in passages]
    
    if dsp.settings.reranker:
        #Gets top-k from SentenceBert, returns list of indexes of k-most relevant passages in passages
        passages_cs_scores = dsp.settings.reranker(query, passages)
        passages_cs_scores_sorted = np.argsort(passages_cs_scores)[::-1]
        #keeps only the top-k indexes in passages
        passages = [passages[idx] for idx in passages_cs_scores_sorted]

    return passages


def retrieveRerankEnsemble(queries: list[str], k: int) -> list[str]:
    if not (dsp.settings.rm and dsp.settings.reranker):
        raise AssertionError("Both RM and Reranker are needed to retrieve & re-rank.")
    queries = [q for q in queries if q]
    passages = {}
    for query in queries:
        retrieved_passages = dsp.settings.rm(query, k=k*3)
        passages_cs_scores = dsp.settings.reranker(query, [psg.long_text for psg in retrieved_passages])
        for idx in np.argsort(passages_cs_scores)[::-1]:
            psg = retrieved_passages[idx]
            passages[psg.long_text] = passages.get(psg.long_text, []) + [
                passages_cs_scores[idx]
            ]

    passages = [(np.average(score), text) for text, score in passages.items()]
    return [text for _, text in sorted(passages, reverse=True)[:k]]


def retrieveEnsemble(queries: list[str], k: int, by_prob: bool = True) -> list[str]:
    """Retrieves passages from the RM for each query in queries and returns the top k passages
    based on the probability or score.
    """
    if not dsp.settings.rm:
        raise AssertionError("No RM is loaded.")
    if dsp.settings.reranker:
        return retrieveRerankEnsemble(queries, k)
    queries = [q for q in queries if q]

    passages = {}
    for q in queries:
        for psg in dsp.settings.rm(q, k=k * 3):
            if by_prob:
                passages[psg.long_text] = passages.get(psg.long_text, 0.0) + psg.prob
            else:
                passages[psg.long_text] = passages.get(psg.long_text, 0.0) + psg.score

    passages = [(score, text) for text, score in passages.items()]
    passages = sorted(passages, reverse=True)[:k]
    passages = [text for _, text in passages]

    return passages
