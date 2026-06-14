import json
from zenml import step
from zenml.logger import get_logger
from source.devil_advocate import DevilAdvocate

logger = get_logger(__name__)

@step
def step_devil_advocate(payload : dict) -> dict:

    logger.info("Launching devil advocate...")

    return DevilAdvocate(payload).devil_advocate()


