from zenml import step
from zenml import get_logger
from source.narrative_generator import NarrativeGenerator

logger = get_logger(__name__)

@step
def step_narrative_generator(findings: dict , hallucination_result : dict , advocate_result : dict) -> dict:

    logger.info("Narrative generator starting...")

    narrative_obj = NarrativeGenerator(findings = findings ,
                       hallucination_result = hallucination_result ,
                       devil_advocate_result = advocate_result)

    result = narrative_obj.narrative_generator()

    return result