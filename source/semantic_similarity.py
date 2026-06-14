import json
from sentence_transformers import SentenceTransformer , util

LOW_SIMILARITY_THRESHOLD = 0.30
SUSPICIOUS_THRESHOLD = 0.25
MAX_ARTIFACT_CHARS = 512

_model = None
MODEL_NAME = "all-MiniLM-L6-v2"

class SemanticSimilarity():

    def __init__(self, grounding_result : dict):

        self.grounding_result = grounding_result


    def _get_model(self , model_name) -> SentenceTransformer:

        global _model

        if _model is None:

            _model = SentenceTransformer(model_name)

        return _model

    def _get_similarity(self , claim : str , artifact_data : dict | None) -> float:

        if artifact_data is None:

            return 0.0

        model = self._get_model(MODEL_NAME)

        artifact_text = json.dumps(artifact_data , ensure_ascii=False)
        artifact_text = artifact_text[:MAX_ARTIFACT_CHARS]

        artifact_emb = model.encode(artifact_text , convert_to_tensor=True)
        claim_emb = model.encode(claim , convert_to_tensor=True)

        similarity = float(util.cos_sim(claim_emb, artifact_emb))

        return round(similarity , 4)

    def semantic_similarity(self , grounding_result : dict) -> dict:

        result = {}

        for hyp_name , hyp_data in self.grounding_result.items():

            grounded_claims = hyp_data.get("grounded_claims" , [])

            similarity_scores = []

            for claim_obj in grounded_claims:

                similarity = self._get_similarity(claim_obj["claim"] , hyp_data.get("artifact_data"))

                similarity_scores.append({
                    "claim" : claim_obj["claim"],
                    "artifact_id" : claim_obj.get("artifact_id"),
                    "similarity" : similarity,
                    "suspicious" : similarity < SUSPICIOUS_THRESHOLD,
                    "low_similarity" : similarity < LOW_SIMILARITY_THRESHOLD
                })

        suspicious = [s for s in similarity_scores if s["suspicious"]]

        total = len(similarity_scores)

        avg_similarity = (sum(s["similarity"] for s in similarity_scores) / total
                          if total > 0 else 0)

        result["hyp_name"] = {
            "similarity_scores" : similarity_scores,
            "avg_similarity" : avg_similarity,
            "suspicious" : suspicious,
        }

        return result