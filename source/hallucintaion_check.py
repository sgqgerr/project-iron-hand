FACT_MIN_SIMILARITY = 0.35
INFERENCE_MIN_SIMILARITY = 0.2
HALLUCINATION_RATE_LIMIT = 0.30

PENALTY_CRITICAL_NLI = 0.15
PENALTY_HIGH_HALLUCINATION = 0.15
PENALTY_LOW_SIMILARITY = 0.1

class HallucinationCheck():

    def __init__(self):

        pass

    def _classify_claim(self , claim_obj : dict , contradicted_facts : set, similarity_map : dict) -> dict:

        claim = claim_obj["claim"]

        is_grounded = claim_obj.get("is_grounded", False)

        artifact_id = claim_obj.get("artifact_id", None)

        similarity = similarity_map.get(claim , 0.0)

        is_contradicted = claim in contradicted_facts

        if is_grounded and similarity >= FACT_MIN_SIMILARITY and not is_contradicted:

            return {
                "claim" : claim,
                "type" : "FACT",
                "artifact_id" : artifact_id,
                "similarity" : similarity,
                "is_grounded" : True,
            }

        elif not is_contradicted and similarity >= INFERENCE_MIN_SIMILARITY:

            return {
                "claim" : claim,
                "type" : "INFERENCE",
                "artifact_id" : artifact_id,
                "similarity" : similarity,
                "is_grounded" : False,
            }

        else:

            return {
                "claim" : claim,
                "type" : "SPECULATION",
                "artifact_id" : None,
                "similarity" : similarity,
            }

    def _apply_penalties(self , original_confidence : float , has_critical_nli : bool , hallucination_rate : float , avg_similarity: float ) -> float:

        revised = original_confidence

        if has_critical_nli:
            revised -= PENALTY_CRITICAL_NLI

        if hallucination_rate:
            revised -= PENALTY_HIGH_HALLUCINATION

        if avg_similarity < 0.25:
            revised -= PENALTY_LOW_SIMILARITY

        return max(round(revised , 3) , 0.01)

    def run_hallucination_check(self , grounding_result : dict , nli_result : dict , similarity_result : dict , devil_advocate_result :dict) -> dict:

        result = {}

        all_hyps = set(grounding_result.keys())

        for hyp_name in all_hyps:

            grounded_claims = grounding_result.get(hyp_name, {}).get("grounded_claims" , [])

            ungrounded_claims = grounding_result.get(hyp_name, {}).get("ungrounded_claims" , [])

            grounding_rate = grounding_result.get(hyp_name, {}).get("grounding_rate", 0.0)

            nli_data = nli_result.get(hyp_name, {})

            has_critical_nli = nli_data.get("has_critical_nli", False)

            contradiction_count = nli_data.get("contradiction_count", 0)

            contradicted_facts = {

                c["fact"] for c in nli_data.get("contradicted_facts", [])
                if c.get("contradiction_score" , 0) > 0.85
            }

            sim_data = similarity_result.get(hyp_name, {})

            avg_similarity = sim_data.get("avg_similarity", 0)

            similarity_map = {

                s["claim"] : s["similarity"]
                for s in sim_data.get("similarity_scores", [])

            }

            da_data = devil_advocate_result.get(hyp_name, {})
            da_revised_confidence = da_data.get("revised_confidence", 0.0)

            all_claims = grounded_claims + ungrounded_claims

            verified_facts = []
            inferences = []
            speculations = []

            for claim_obj in all_claims:

                classified = self._classify_claim(
                    claim_obj,
                    contradicted_facts,
                    similarity_map
                )

                if classified["type"] == "FACT":

                    verified_facts.append(classified)

                elif classified["type"] == "INFERENCE":

                    inferences.append(classified)

                else :

                    speculations.append(classified)

            total_meaningful = len(verified_facts) + len(inferences)

            hallucination_rate = (
                len(inferences) / total_meaningful
                if total_meaningful > 0 else 0
            )

            revised_confidence = self._apply_penalties(
                original_confidence = da_revised_confidence,
                has_critical_nli = has_critical_nli,
                hallucination_rate = hallucination_rate,
                avg_similarity = avg_similarity
            )

            result[hyp_name] = {

                "verified_facts" : verified_facts,
                "inferences" : inferences,
                "speculations" : speculations,
                "hallucination_rate" : hallucination_rate,
                "revised_confidence" : revised_confidence,
                "guard_summary" : {
                    "grounding_rate" : grounding_rate,
                    "contradiction_count" : contradiction_count,
                    "has_critical_nli" : has_critical_nli,
                    "avg_similarity" : avg_similarity,
                    "facts_count" : len(verified_facts),
                    "inferences_count" : len(inferences),
                    "speculations_count" : len(speculations),
                }
            }

        return result