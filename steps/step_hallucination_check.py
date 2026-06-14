from typing import Annotated
from zenml import step
from zenml.logger import get_logger
from source.hallucination_check import HallucinationCheck

logger = get_logger(__name__)

@step
def step_hallucination_check(grounding_result, semantic_result, nli_result, devil_advocate_result):

    return HallucinationCheck().run_hallucination_check(

        grounding_result=grounding_result,

        similarity_result=semantic_result,

        nli_result=nli_result,

        devil_advocate_result=devil_advocate_result,

    )