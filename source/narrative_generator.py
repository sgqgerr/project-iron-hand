import os
from google import genai
from google.genai import types
import json

API_KEY = os.getenv("API_KEY")

client  = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are a senior forensic analyst writing an IR report.
Rules:
  - Mark confirmed facts as [FACT: artifact_id]
  - Mark inferences as [INFERENCE]
  - Cite evidence for every claim
  - Include counter-arguments section
  - Professional language, max 600 words
  - Output Markdown only"""

USER_PROMPT_TEMPLATE = """Write an IR report based on this data:
{report_json}

Structure:
1. Executive Summary (2-3 sentences)
2. Score Summary (table: artifact | score | status)
3. Discrepancy Analysis (if memory vs logs diverge significantly)
4. Timeline of Events
5. Technical Evidence
6. Counter-arguments
7. Verdict and Recommended Actions"""


class NarrativeGenerator:

    def __init__(self, findings: dict, hallucination_result: dict, devil_advocate_result: dict):

        self.findings = findings

        self.hallucination_result  = hallucination_result

        self.devil_advocate_result = devil_advocate_result

    def _build_report_input(self) -> dict:

        hypotheses_summary = {}

        for hyp_name, hyp_data in self.hallucination_result.items():
            hypotheses_summary[hyp_name] = {
                "revised_confidence": hyp_data.get("revised_confidence", 0.0),
                "hallucination_rate": hyp_data.get("hallucination_rate", 0.0),
                "verified_facts":     hyp_data.get("verified_facts", []),
                "inferences":         hyp_data.get("inferences", []),
                "counter_arguments":  self.devil_advocate_result.get(hyp_name, {}).get("counter_arguments", []),
                "guard_summary":      hyp_data.get("guard_summary", {}),
            }

        return {
            "case_id":     self.findings.get("case_id"),
            "ml1-scores":  self.findings.get("scores", {}),
            "discrepancy": self.findings.get("discrepancy", {}),
            "hypotheses":  hypotheses_summary,
            "audit_steps": self.findings.get("audit_steps", []),
        }

    def _determine_verdict(self) -> dict:

        best_hyp  = None

        best_conf = 0.0

        for hyp_name, hyp_data in self.hallucination_result.items():

            conf = hyp_data.get("revised_confidence", 0.0)

            if conf > best_conf:

                best_conf = conf

                best_hyp  = hyp_name

        if best_hyp == "false_positive" or best_conf < 0.45:

            risk = "LOW"

        elif best_conf < 0.75:

            risk = "MEDIUM"

        else:

            risk = "HIGH"

        return {
            "leading_hypothesis": best_hyp,
            "confidence":         round(best_conf, 3),
            "risk":               risk,
        }

    def narrative_generator(self) -> dict:

        verdict      = self._determine_verdict()

        report_input = self._build_report_input()

        report_json = json.dumps(report_input, ensure_ascii=False, indent=2)

        if len(report_json) > 6000:

            report_json = report_json[:6000] + "\n[truncated]"

        user_prompt = USER_PROMPT_TEMPLATE.format(report_json=report_json)

        try:

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=user_prompt,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
            )
            narrative_md = response.text.strip()

        except Exception as exc:

            narrative_md = f"## Error generating narrative\n\n{exc}"

        rates = [
            h["hallucination_rate"]
            for h in self.hallucination_result.values()
            if "hallucination_rate" in h
        ]
        overall_hallucination_rate = round(sum(rates) / len(rates), 4) if rates else 0.0

        all_verified_facts    = []
        all_inferences        = []
        all_counter_arguments = []

        for hyp_name, hyp_data in self.hallucination_result.items():

            all_verified_facts.extend(hyp_data.get("verified_facts", []))

            all_inferences.extend(hyp_data.get("inferences", []))

            all_counter_arguments.extend(
                self.devil_advocate_result.get(hyp_name, {}).get("counter_arguments", [])
            )

        top_confidence = max(
            (h.get("revised_confidence", 0.0) for h in self.hallucination_result.values()),
            default=0.0,
        )
        top_hallucination = max(
            (h.get("hallucination_rate", 0.0) for h in self.hallucination_result.values()),
            default=0.0,
        )

        return {
            "narrative_md":               narrative_md,
            "verdict":                    verdict,
            "overall_hallucination_rate": overall_hallucination_rate,
            "final_confidence":           verdict["confidence"],
            "verified_facts":             all_verified_facts,
            "inferences":                 all_inferences,
            "counter_arguments":          all_counter_arguments,
            "revised_confidence":         round(top_confidence, 3),
            "hallucination_rate":         round(top_hallucination, 4),
        }