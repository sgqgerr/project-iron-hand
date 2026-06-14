from source.nli import NLI_Classification
from zenml import get_logger
from zenml import step

logger = get_logger.get_logger(__name__)

@step
def step_nli_classification(grounding_result : dict , devil_advocate_result : dict) -> dict:

    logger.info("Launching NLI classification...")

    nli_obj = NLI_Classification(grounding_result = grounding_result ,
                       devil_advocate_result = devil_advocate_result)

    return nli_obj.nli_check(
        grounding_result=grounding_result,
        devil_advocate_result=devil_advocate_result,
    )