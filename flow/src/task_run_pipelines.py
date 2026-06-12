import json
import logging
from typing import Any

import redis
from prefect import task

from logs_handler.pipelines.pipeline_log_model_predict import pipeline_log_model_predict
from logs_handler.pipelines.pipeline_log_model_train import pipeline_log_model_train
from memory_handler.pipelines.pipeline_memory_model_launch import pipeline_memory_model_launch
from memory_handler.pipelines.pipeline_memory_model_train import pipeline_memory_model_train

logger = logging.getLogger(__name__)

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_RESULT_TTL = 3600
REDIS_KEY_PREFIX = "ml1:result"


def _redis_client() -> redis.Redis:

    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
    )

def _store_result(r: redis.Redis, case_id: str, result: dict) -> None:

    key = f"{REDIS_KEY_PREFIX}:{case_id}"

    r.setex(key, REDIS_RESULT_TTL, json.dumps(result))

    logger.debug("Stored result in Redis key=%s", key)


def _run_predict(job: dict[str, Any]) -> dict[str, Any]:

    case_id: str = job["case_id"]
    log_path: str = job.get("log_path", "")

    # --- Log model predict ---

    log_result = {}

    if log_path:

        logger.info("[%s] Running pipeline_log_model_predict", case_id)

        log_result = pipeline_log_model_predict(
            log_path=log_path,
            case_id=case_id,
        )

    else:

        logger.warning("[%s] No log_path provided — skipping log pipeline", case_id)

    # --- Memory model predict ---

    memory_result = {}

    parsed_cases = job.get("parsed_memory_cases")

    labels = job.get("labels")

    if parsed_cases is not None and labels is not None:

        logger.info("[%s] Running pipeline_memory_model_launch", case_id)

        memory_result = pipeline_memory_model_launch(
            parsed_cases=parsed_cases,
            labels=labels,
            case_id=case_id,
        )
    else:

        logger.info("[%s] No parsed_memory_cases — skipping memory pipeline", case_id)

    return {
        "case_id": case_id,
        "mode": "predict",
        "log_result": log_result,
        "memory_result": memory_result,
        "status": "ok",
    }


def _run_train(job: dict[str, Any]) -> dict[str, Any]:

    case_id: str = job["case_id"]

    log_path: str = job.get("log_path", "")

    y_train = job.get("y_train")

    n_synthetic: int = job.get("n_synthetic", 500)

    # --- Log model train ---

    if log_path and y_train is not None:

        logger.info("[%s] Running pipeline_log_model_train", case_id)

        pipeline_log_model_train(
            log_path=log_path,
            case_id=case_id,
            y_train=y_train,
        )

    else:

        logger.warning(
            "[%s] Skipping log train — missing log_path or y_train", case_id
        )

    # --- Memory model train ---

    logger.info("[%s] Running pipeline_memory_model_train (n=%d)", case_id, n_synthetic)

    pipeline_memory_model_train(
        case_id=case_id,
        n=n_synthetic,
    )

    return {
        "case_id": case_id,
        "mode": "train",
        "status": "ok",
    }

@task(
    name="run-zenml-pipelines",
    retries=1,
    retry_delay_seconds=10,
    tags=["zenml", "pipeline", "ml1"],
)
def task_run_pipelines(
    jobs: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    if not jobs:

        logger.info("No jobs to process — returning empty list")

        return []

    r = _redis_client()

    results: list[dict[str, Any]] = []

    for job in jobs:

        case_id = job.get("case_id", "unknown")

        mode = job.get("mode", "predict")

        logger.info("Processing case_id=%s mode=%s", case_id, mode)

        try:

            if mode == "train":

                result = _run_train(job)

            else:

                result = _run_predict(job)

            _store_result(r, case_id, result)

            results.append(result)

        except Exception as exc:

            logger.error(
                "Pipeline failed for case_id=%s: %s", case_id, exc, exc_info=True
            )

            error_result = {
                "case_id": case_id,
                "mode": mode,
                "status": "error",
                "error": str(exc),
            }

            _store_result(r, case_id, error_result)

            results.append(error_result)

    logger.info(

        "Finished batch: %d ok, %d errors",

        sum(1 for r in results if r["status"] == "ok"),

        sum(1 for r in results if r["status"] == "error"),
    )

    return results