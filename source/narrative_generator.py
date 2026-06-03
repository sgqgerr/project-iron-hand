import asyncio
import os
from google import genai
from google.genai import types
import json


API_KEY = os.getenv("API_KEY")

client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are a senior forensic analyst writing an IR report.
                                  Rules:
                                    - Mark confirmed facts as [FACT: artifact_id]
                                    - Mark inferences as [INFERENCE]
                                    - Cite evidence for every claim
                                    - Include counter-arguments section
                                    - Professional language, max 600 words
                                    - Output Markdown only
                                """
USER_PROMPT = """Write an IR report based on this data:
                      {json_with_verified_facts_and_counter_args}
                
                      Structure:
                      1. Executive Summary (2-3 sentences)
                      2. Score Summary (table: artifact | score | status)
                      3. Discrepancy Analysis (якщо memory vs logs сильно розходяться)
                      4. Timeline of Events
                      5. Technical Evidence
                      6. Counter-arguments
                      7. Verdict and Recommended Actions
                 """
class NarrativeGenerator():

    def __init__(self , findings: dict , hallucination_result : dict , devil_advocate_result : dict):

        self.findings = findings,
        self.hallucination_result = hallucination_result
        self.devil_advocate_result = devil_advocate_result

        pass

    def _build_report_input(self, findings : dict , hallucination_result : dict , devil_advocate_result : dict) -> dict:

        hypotheses_summary = {}

        for hyp_name , hyp_data in hallucination_result.items():

            hypotheses_summary[hyp_name] = {

                "revised_confidence" : hyp_data["revised_confidence"],
                "hallucination_rate" : hyp_data["hallucination_rate"],
                "verified_facts" : hyp_data["verified_facts"],
                "inferences" : hyp_data["inferences"],
                "counter_arguments" : devil_advocate_result.get("hyp_name" , {}).get("counter_arguments", []),
                "guard_summary" : hyp_data["guard_summary"],

            }

        return {

            "case_id" : findings.get("case_id"),
            "ml1-scores" : findings.get("scores" , {}),
            "discrepancy" : findings.get("discrepancy" , {}),
            "hypotheses" : hypotheses_summary,
            "audit_steps" : findings.get("audit_steps" , []),

        }

    def _determine_verdict(self , hallucination_result : dict) -> dict:

        best_hype = None
        best_conf = 0.0

        for hyp_name , hyp_data in hallucination_result.items():

            conf = hyp_data.get("revised_confidence" , 0.0)

            if conf > best_conf:

                best_conf = conf
                best_hype = hyp_name

        if best_hype == "false_positive" or best_conf < 0.45:

            risk = "LOW"

        elif best_conf < 0.75:

            risk = "MEDIUM"

        else:

            risk = "HIGH"

        return {
            "leading_hypothesis" : best_hype,
            "confidence" : round(best_conf, 3),
            "risk" : risk,
        }

    def narrative_generator(self, findings: dict , hallucination_result : dict , devil_advocate_result : dict) -> dict:

        verdict = self._determine_verdict(hallucination_result)

        report_input = self._build_report_input(

            finding = findings,
            hallucination_result = hallucination_result,
            devil_advocate_result = devil_advocate_result

        )

        report_json = json.dumps(report_input , ensure_ascii = False, indent = 2)

        if len(report_json) > 6000:

            report_json = report_json[:6000] + "\n [truncated]"

        try :

            response = client.models.generate_content(

                model = MODEL_NAME,
                contents = USER_PROMPT,
                config = types.GenerateContentConfig(

                    system_instruction=SYSTEM_PROMPT,

                )
            )

            narrative_md = response.content[0].strip()

        except Exception as e:

            narrative_md = f"## Error generating narrative\n\n{e}"

        rates = [

            h["hallucination_rate"]
            for h in hallucination_result.values()
            if "hallucination_rate" in h

        ]

        overall_hallucination_rate = (
            round(sum(rates) / len(rates), 4) if rates else 0
        )

        return {
            "narrative" : narrative_md,
            "verdict" : verdict,
            "overall_hallucination_rate" : overall_hallucination_rate,
            "final_confidence" : verdict["confidence"],
        }

