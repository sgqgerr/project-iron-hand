from zenml import step
from zenml import logger
from source.grounding_verification import GroundingVerification

logger = logger.get_logger(__name__)

@step
def step_grounding_verification(advocate_result : dict) -> dict:

    logger.info("Launching grounding verification...")

    grounding_obj = GroundingVerification(advocate_result)

    result = grounding_obj.grounding_verification()

    return result