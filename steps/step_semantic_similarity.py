from source.semantic_similarity import SemanticSimilarity
from zenml import get_logger
from zenml import step

logger = get_logger(__name__)

@step
def step_semantic_similarity(grounding_result : dict) -> dict:

    logger.info("Launching semantic similarity...")

    semantic_obj = SemanticSimilarity(grounding_result = grounding_result)

    result = semantic_obj.semantic_similarity()

    return result