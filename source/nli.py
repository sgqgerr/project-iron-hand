from transformers import pipeline
import logging

_model = None
NLI_MODEL = "cross-encoder/nli-deberta-v3-small"
CRITICAL_THRESHOLD = 0.93
CONTRADICTION_THRESHOLD = 0.85

class NLI_Classification():

    def __init__(self, grounding_result : dict , devil_advocate_result : dict):

        self.grounding_result = grounding_result

        self.devil_advocate_result = devil_advocate_result



    def _load_model(self):

        global _model

        try :
            if _model is None:

                _model = pipeline("text-classification", model=NLI_MODEL)
                return _model

        except Exception as e:

            logging.error(e)

    def _check_pair(self , fact : str , counter : str) -> dict :

        _model = self._load_model()

        input_text = f"{fact} [SEP] {counter}"

        result = _model(input_text)

        return {
            "label" : result["label"],
            "score" : round(result["score"], 2),
            "is_contradiction" : (result["label"] == "CONTRADICTION" and
                                  result["score"] >= CONTRADICTION_THRESHOLD),
            "is_critical" : (result["label"] == "CRITICAL" and
                             result["score"] >= CRITICAL_THRESHOLD),
        }

    def nli_check(self , grounding_result : dict , devil_advocate_result : dict) -> dict :

        result = {}

        all_hyps = set(grounding_result.keys()) | set(devil_advocate_result.keys())

        for hyp_name in all_hyps:

            grounded_claims = grounding_result.get(hyp_name , {}).get("grounded_claims" , [])

            counter_arguments = devil_advocate_result.get(hyp_name , {}).get("counter_arguments" , [])

            contradictions = []

            for fact_obj in grounded_claims :

                for counter_obj in counter_arguments :

                    pair_result = self._check_pair(fact_obj["claim"] , counter_obj["argument"])

                    if pair_result["is_contradiction"] :

                        contradictions.append({
                            "fact": fact_obj["claim"],
                            "fact_artifact_id": fact_obj.get("artifact_id"),
                            "counter": counter_obj["argument"],
                            "counter_artifact_id": counter_obj.get("artifact_id"),
                            "contradiction_score": pair_result["score"],
                            "is_critical": pair_result["is_critical"],
                        })
            result[hyp_name] = {
                "contradictions" : contradictions,
                "contradiction_count" : len(contradictions),
                "is_critical" : any(c["is_critical"] for c in contradictions),
            }

        return result