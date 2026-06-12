import json
import logging
from typing import Any

from kafka import KafkaConsumer
from kafka.errors import KafkaError
from prefect import task

logger = logging.getLogger(__name__)

REDPANDA_BROKERS = ["localhost:9092"]

INPUT_TOPIC = "ir.jobs.incoming"

CONSUMER_GROUP = "ml1-flow-consumer"

POLL_TIMEOUT_MS = 5_000

MAX_MESSAGES = 50

@task(
    name="consume-ir-jobs",
    description="Pull a batch of IR analysis jobs from Redpanda (BE2 → ML1 queue).",
    retries=2,
    retry_delay_seconds=5,
    tags=["redpanda", "consumer", "ml1"],
)
def task_consume_data(
    brokers: list[str] = REDPANDA_BROKERS,
    topic: str = INPUT_TOPIC,
    group_id: str = CONSUMER_GROUP,
    max_messages: int = MAX_MESSAGES,
    poll_timeout_ms: int = POLL_TIMEOUT_MS,
) -> list[dict[str, Any]]:

    logger.info(
        "Connecting to Redpanda | brokers=%s | topic=%s | group=%s",
        brokers, topic, group_id,
    )

    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=brokers,
        group_id=group_id,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        consumer_timeout_ms=poll_timeout_ms,
        value_deserializer=lambda raw: raw,
        max_poll_records=max_messages,
    )

    jobs: list[dict[str, Any]] = []

    raw_messages = []

    try:

        for message in consumer:

            try:

                payload = json.loads(message.value.decode("utf-8"))

            except (json.JSONDecodeError, UnicodeDecodeError) as exc:

                logger.warning(

                    "Skipping malformed message offset=%d: %s",

                    message.offset, exc,

                )

                continue


            case_id = payload.get("case_id")

            if not case_id:

                logger.warning("Message missing case_id — skipping: %s", payload)

                continue

            jobs.append(payload)

            raw_messages.append(message)

            if len(jobs) >= max_messages:
                break

    except KafkaError as exc:

        logger.error("Kafka consumer error: %s", exc)

        raise

    finally:

        if raw_messages:

            # Commit only the offsets , that were actually consumed

            consumer.commit()

            logger.info("Committed %d offsets", len(raw_messages))

        consumer.close()

    logger.info("Consumed %d jobs from topic '%s'", len(jobs), topic)

    return jobs