from typing import Annotated
from zenml import step
from zenml.logger import get_logger
from source.hallucintaion_check import HallucinationCheck

logger = get_logger(__name__)

@step
def step_hallucination_check(grounding_result : dict, similarity_result : dict,
                             nli_result : dict , devil_advocate_result : dict) -> Annotated[dict, "hallucination_report"]:

    logger.info("Launching hallucination check...")

    hal_check_obj = HallucinationCheck()

    result = hal_check_obj.run_hallucination_check(grounding_result = grounding_result,
                                                   similarity_result = similarity_result ,
                                                   nli_result = nli_result,
                                                   devil_advocate_result = devil_advocate_result)

    return result