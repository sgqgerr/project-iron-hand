from zenml import step
from zenml import get_logger
import redis
from source.grounding_verification import GroundingVerification

logger = get_logger(__name__)

def step_grounding_verification(payload: dict, devil_advocate_result: dict) -> dict:

    r = redis.Redis(host="localhost", port=6379, decode_responses=True)

    obj = GroundingVerification(claim="", client=r, findings=payload)

    return obj.grounding_verification(findings=payload)