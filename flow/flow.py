import logging
import sys

from prefect import flow, get_run_logger
from prefect.states import Failed

from src.task_consume_data import task_consume_data
from src.task_publish_data import task_publish_data
from src.task_run_pipelines import task_run_pipelines

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
)

@flow(
    name="ml1-iron-hand-flow",
    description=(
        "Autonomous IR pipeline: consume BE2 jobs from Redpanda → "
        "run ZenML log + memory scoring pipelines → publish results back."
    ),
    version="1.0.0",
    retries=0,
    log_prints=True,
)
def ml1_flow(
    brokers: list[str] | None = None,
    input_topic: str = "ir.jobs.incoming",
    output_topic: str = "ir.results.ml1",
    consumer_group: str = "ml1-flow-consumer",
    max_messages: int = 50,
) -> dict:

    logger = get_run_logger()

    _brokers = brokers or ["localhost:9092"]

    logger.info(
        "ml1_flow started | brokers=%s | in=%s | out=%s | max=%d",

        _brokers, input_topic, output_topic, max_messages,
    )

    jobs = task_consume_data(

        brokers=_brokers,

        topic=input_topic,

        group_id=consumer_group,

        max_messages=max_messages,

    )

    if not jobs:

        logger.info("No jobs in queue — flow finished early (nothing to process)")

        return {"consumed": 0, "published": 0, "failed": 0}

    logger.info("Consumed %d jobs", len(jobs))

    results = task_run_pipelines(jobs=jobs)

    ok_count = sum(1 for r in results if r.get("status") == "ok")

    err_count = sum(1 for r in results if r.get("status") == "error")

    logger.info("Pipelines done | ok=%d errors=%d", ok_count, err_count)

    publish_summary = task_publish_data(

        results=results,

        brokers=_brokers,

        topic=output_topic,

    )

    summary = {
        "consumed": len(jobs),
        "pipeline_ok": ok_count,
        "pipeline_errors": err_count,
        "published": publish_summary["published"],
        "publish_failed": publish_summary["failed"],
    }

    logger.info("ml1_flow finished | %s", summary)

    if publish_summary["failed"] > 0:

        logger.warning(

            "%d results failed to publish — check Redpanda connectivity",

            publish_summary["failed"],

        )

    return summary

if __name__ == "__main__":
    result = ml1_flow()
    print("\nFlow result:", result)