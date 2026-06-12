import json
import logging
from typing import Any

from kafka import KafkaProducer
from kafka.errors import KafkaError
from prefect import task

logger = logging.getLogger(__name__)

REDPANDA_BROKERS = ["localhost:9092"]

OUTPUT_TOPIC = "ir.results.ml1"

PRODUCER_ACKS = "all"

PRODUCER_LINGER_MS = 10


@task(
    name="publish-ml1-results",
    retries=3,
    retry_delay_seconds=5,
    tags=["redpanda", "producer", "ml1"],
)

def task_publish_data(
    results: list[dict[str, Any]],
    brokers: list[str] = REDPANDA_BROKERS,
    topic: str = OUTPUT_TOPIC,
) -> dict[str, int]:

    if not results:

        logger.info("No results to publish — skipping producer")

        return {"published": 0, "failed": 0}

    logger.info(
        "Connecting to Redpanda | brokers=%s | topic=%s | batch_size=%d",
        brokers, topic, len(results),
    )

    producer = KafkaProducer(
        bootstrap_servers=brokers,
        acks=PRODUCER_ACKS,
        linger_ms=PRODUCER_LINGER_MS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
    )

    published = 0
    failed = 0

    for result in results:

        case_id: str = result.get("case_id", "")

        try:

            future = producer.send(
                topic=topic,
                key=case_id,
                value=result,
            )

            # Block with timeout to surface per-message errors

            record_metadata = future.get(timeout=10)

            logger.debug(
                "Published case_id=%s → topic=%s partition=%d offset=%d",
                case_id,
                record_metadata.topic,
                record_metadata.partition,
                record_metadata.offset,
            )

            published += 1

        except KafkaError as exc:

            logger.error(
                "Failed to publish case_id=%s: %s", case_id, exc, exc_info=True
            )

            failed += 1

    try:

        producer.flush(timeout=15)

    except KafkaError as exc:

        logger.error("Producer flush failed: %s", exc)
    finally:

        producer.close()


    logger.info(

        "Publish complete | published=%d failed=%d | topic=%s",

        published, failed, topic,

    )

    return {"published": published, "failed": failed}