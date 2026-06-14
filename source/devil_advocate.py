import os
from google import genai
from google.genai import types
import json
import logging

API_KEY = os.getenv("API_KEY")

client = genai.Client(api_key=API_KEY)

SEVERITY_PENALTY = {
    "high":   0.15,
    "medium": 0.07,
    "low":    0.03,
}

def recalculate_confidence(old_confidence: float, counter_arguments: list) -> float:
    total_penalty = sum(
        SEVERITY_PENALTY.get(arg.get("severity", "low"), 0.03)
        for arg in counter_arguments
    )

    return max(round(old_confidence - total_penalty, 3), 0.01)

class DevilAdvocate():

    def __init__(self , payload):

        self.payload = payload

    def devil_advocate(self):

        hypotheses = self.payload.get("hypothesis", {})

        artifact_ids = [a.get("artifact_id") for a in self.payload.get("artifacts", []) if a.get("artifact_id") is not None]

        if not hypotheses:

            return {}

        results = {}

        for hypo_name , hypo_data in hypotheses.items():

            confidence = hypo_data.get("confidence", 0)

            for_list = hypo_data.get("for_list", [])

            against_list = hypo_data.get("against_list", [])


            user_prompt = f"""Hypothesis: {hypo_name} (confidence: {confidence})
                                Evidence FOR: {for_list}
                                Evidence AGAINST: {against_list}
                                Available artifact IDs: {artifact_ids}
                                
                                Find 3 reasons why this conclusion might be WRONG.
                                For each reason, cite which artifact_id could support it.
                                Return JSON:
                                {{
                                  "counter_arguments": [
                                    {{"argument": "string", "artifact_id": "string or null",
                                      "severity": "high or medium or low"}}
                                  ],
                                  "revised_confidence": 0.0,
                                  "reasoning": "string"
                                }}"""

            system_prompt = """You are a senior forensic analyst playing devil's advocate.
                               Your job is to challenge conclusions, not confirm them.
                               Respond ONLY with valid JSON. No markdown, no preamble."""

            raw_text = ""

            try :

                response = client.models.generate_content(

                    model="gemini-2.5-flash",
                    contents = user_prompt,
                    config = types.GenerateContentConfig(
                    system_instruction= system_prompt)

                    )

                raw_text = response.text.strip()

                parsed = json.loads(raw_text)

                counter_args = parsed.get("counter_arguments", [])


                revised_confidence = recalculate_confidence(confidence, counter_args)
                delta = round(revised_confidence - confidence, 3)

                results[hypo_name] = {
                    "original_confidence": confidence,
                    "revised_confidence": revised_confidence,
                    "delta": delta,
                    "counter_arguments": parsed.get("counter_arguments", []),
                    "reasoning": parsed.get("reasoning", ""),
                }


            except json.JSONDecodeError as e:

                logging.error(f"[{hypo_name}] Invalid JSON from Gemini: {e}")

                logging.error(f"Raw text was: {raw_text}")

                results[hypo_name] = {"error": "invalid_json", "delta": 0.0}


            except Exception as e:

                logging.error(f"[{hypo_name}] Gemini call failed: {e}")

                results[hypo_name] = {"error": str(e), "delta": 0.0}

        return results
