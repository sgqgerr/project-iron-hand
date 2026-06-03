import asyncio
import os
import json
import logging
from google import genai
import redis.asyncio as aioredis
from kafka import KafkaConsumer, KafkaProducer
from kafka.cli.admin import topics

from pipelines.main_pipeline import main_pipeline

logging.basicConfig(level=logging.INFO)

API_KEY = os.getenv("API_KEY")
client  = genai.Client(api_key=API_KEY)
inst    = aioredis.Redis(host="localhost", port=6379, decode_responses=True)

REDPANDA_BOOTSTRAP = os.getenv("REDPANDA_BOOTSTRAP", "localhost:9092")

consumer = KafkaConsumer(
    topics = "agent-findings",
    bootstrap_servers=REDPANDA_BOOTSTRAP,
    value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    group_id="ml2-doubt-engine",
    auto_offset_reset="earliest",
)

producer = KafkaProducer(
    bootstrap_servers=REDPANDA_BOOTSTRAP,
    value_serializer=lambda x: json.dumps(x).encode("utf-8"),
)


async def main() -> None:
    logging.info("ML2 Doubt Engine started — listening to agent-findings...")

    while True:

        records = await asyncio.to_thread(
            consumer.poll, 100
        )

        if not records:
            continue

        for _, messages in records.items():
            for msg in messages:
                payload = msg.value
                case_id = payload.get("case_id")

                try:
                    logging.info(f"[{case_id}] received from agent-findings")

                    narrative_report = await asyncio.to_thread(
                        main_pipeline, payload
                    )

                    verified_payload = {
                        "case_id":            case_id,
                        "verified_facts":     narrative_report.get("verified_facts", []),
                        "inferences":         narrative_report.get("inferences", []),
                        "counter_arguments":  narrative_report.get("counter_arguments", []),
                        "revised_confidence": narrative_report.get("revised_confidence", 0.0),
                        "hallucination_rate": narrative_report.get("hallucination_rate", 0.0),
                        "narrative_md":       narrative_report.get("narrative_md", ""),
                    }


                    await asyncio.to_thread(
                        producer.send,
                        "ml2-verified-findings",
                        verified_payload
                    )
                    await asyncio.to_thread(producer.flush)


                    await inst.set(
                        f"pipeline:{case_id}:state",
                        json.dumps({"step": "ml2_complete", "status": "done"}),
                        ex=86400
                    )

                    logging.info(
                        f"[{case_id}] pushed to ml2-verified-findings | "
                        f"confidence: {verified_payload['revised_confidence']} | "
                        f"hallucination_rate: {verified_payload['hallucination_rate']}"
                    )

                except Exception as e:
                    logging.error(f"[{case_id}] Failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())