import redis as r
import json

class GroundingVerification():

    def __init__(self, claim : str , client : r.Redis , findings : dict) -> None:

        self.claim = claim

        self.client = client

        self.findings = findings



    def connect(self) -> r.Redis:

        return r.Redis(host='localhost',
                       port=6379,
                       decode_responses=True)


    def _verify_claim(self , claim : str , redis_client : r.Redis) -> dict:

        import re

        pattern = r'/b([a-z_]+_[a-f0-9]{4,8})/b'
        matches = re.findall(pattern , claim.lower())

        artifact_id = matches[0] if matches else None

        grounded = True

        artifact_data = None

        if artifact_id:

            raw = redis_client.get(f"artifact:{artifact_id}")

            if raw:

                try:
                    artifact_data = json.loads(raw)

                    grounded = True

                except json.decoder.JSONDecodeError:

                    grounded = False

        return {
            "claim" : claim,
            "artifact_id" : artifact_id,
            "artifact_data" : artifact_data,
            "grounded" : grounded
        }

    def grounding_verification(self , findings : dict) -> dict:

        redis_client = self.connect()

        hypothesis_map = findings.get("hypothesis" , {})

        results = {}

        for hyp_name , hyp_data in hypothesis_map.items():

            frl = hyp_data.get("for" , [])

            grounded = []
            ungrounded = []

            for claim in frl:

                verified = self._verify_claim(claim , redis_client)

                if verified["grounded"]:

                    grounded.append(verified["claim"])

                else :

                    ungrounded.append(verified["claim"])

            total = len(grounded) + len(ungrounded)

            grounding_rate = len(grounded) / total if total > 0 else 0.0

            results[hyp_name] = {
                "grounded_claims" : grounded,
                "ungrounded_claims" : ungrounded,
                "grounding_rate" : grounding_rate
            }

        return results