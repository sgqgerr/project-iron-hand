from zenml import pipeline
from steps.step_devil_advocate import step_devil_advocate
from steps.step_hallucination_check import step_hallucination_check
from steps.step_narrative_generator import step_narrative_generator
from steps.step_grounding_verification import step_grounding_verification
from steps.step_semantic_similarity import step_semantic_similarity
from steps.step_nli import step_nli_classification

@pipeline
def main_pipeline(payload : dict) -> dict:

    advocate_result = step_devil_advocate(payload = payload)

    grounding_result = step_grounding_verification(devil_advocate_result = advocate_result)

    nli_result = step_nli_classification(grounding_result = grounding_result, devil_advocate_result = advocate_result)

    semantic_result = step_semantic_similarity(grounding_result = grounding_result)

    hallucination_result = step_hallucination_check(devil_advocate_result = advocate_result ,
                                                    semantic_result = semantic_result ,
                                                    grounding_result = grounding_result ,
                                                    nli_result = nli_result)

    narrative_report = step_narrative_generator(advocate_result = advocate_result ,
                                                hallucination_result = hallucination_result)

    return narrative_report