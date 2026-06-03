import json
from zenml import step
from zenml.logger import get_logger
from source.devil_advocate import DevilAdvocate

logger = get_logger(__name__)

@step
def step_devil_advocate(payload : json.JSONDecoder):

    logger.info("Launching devil advocate...")

    devil_advocate_obj = DevilAdvocate(payload)

    result = devil_advocate_obj.devil_advocate()

    return result


