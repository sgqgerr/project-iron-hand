import uvicorn
import asyncio
import os
import json
import logging
from contextlib import asynccontextmanager

from google import genai
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pipelines.main_pipeline import main_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")

log = logging.getLogger("ml2")

API_KEY = os.getenv("API_KEY")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")

REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

REDPANDA_BROKERS = os.getenv("REDPANDA_BOOTSTRAP", "localhost:9092")

MODE = os.getenv("MODE", "http")

client = genai.Client(api_key=API_KEY)
inst   = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

class AnalyzeRequest(BaseModel):
    case_id: str
    hypothesis: dict = {}
    artifacts: list = []
    scores: dict = {}
    discrepancy: dict = {}
    audit_steps: list = []


class AnalyzeResponse(BaseModel):
    case_id: str
    verified_facts:     list
    inferences:         list
    counter_arguments:  list
    revised_confidence: float
    hallucination_rate: float
    narrative_md:       str
    verdict:            dict
    overall_hallucination_rate: float

@asynccontextmanager
async def lifespan(app: FastAPI):

    log.info("ML2 Doubt Engine HTTP mode starting")

    yield

    log.info("ML2 shutting down")

app = FastAPI(
    title="Iron Hand — ML2 Doubt Engine",
    description="Hallucination detection, devil's advocate, NLI verification, narrative generation.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():

    redis_ok = True

    try:

        await inst.ping()


    except Exception:

        redis_ok = False

    return {"status": "ok", "redis": redis_ok, "mode": MODE}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):

    payload = req.model_dump()

    case_id = payload["case_id"]

    log.info("[%s] HTTP /analyze received", case_id)

    try:

        narrative_report = await asyncio.to_thread(main_pipeline, payload)

    except Exception as exc:

        log.error("[%s] Pipeline failed: %s", case_id, exc, exc_info=True)

        raise HTTPException(status_code=500, detail=str(exc))

    result = {
        "case_id":                  case_id,
        "verified_facts":           narrative_report.get("verified_facts", []),
        "inferences":               narrative_report.get("inferences", []),
        "counter_arguments":        narrative_report.get("counter_arguments", []),
        "revised_confidence":       narrative_report.get("revised_confidence", 0.0),
        "hallucination_rate":       narrative_report.get("hallucination_rate", 0.0),
        "narrative_md":             narrative_report.get("narrative_md", ""),
        "verdict":                  narrative_report.get("verdict", {}),
        "overall_hallucination_rate": narrative_report.get("overall_hallucination_rate", 0.0),
    }

    try:

        await inst.set(
            f"ml2:result:{case_id}",
            json.dumps(result),
            ex=86400,
        )
        await inst.set(
            f"pipeline:{case_id}:state",
            json.dumps({"step": "ml2_complete", "status": "done"}),
            ex=86400,
        )
    except Exception as exc:
        log.warning("[%s] Redis write failed: %s", case_id, exc)

    log.info(
        "[%s] done | confidence=%.3f | hallucination=%.3f",
        case_id,
        result["revised_confidence"],
        result["hallucination_rate"],
    )
    return result


@app.get("/result/{case_id}")
async def get_result(case_id: str):

    raw = await inst.get(f"ml2:result:{case_id}")

    if not raw:

        raise HTTPException(status_code=404, detail=f"No result for case_id={case_id}")

    return json.loads(raw)

async def kafka_loop():
    from kafka import KafkaConsumer, KafkaProducer

    consumer = KafkaConsumer(
        "agent-findings",
        bootstrap_servers=REDPANDA_BROKERS,
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        group_id="ml2-doubt-engine",
        auto_offset_reset="earliest",
    )
    producer = KafkaProducer(
        bootstrap_servers=REDPANDA_BROKERS,
        value_serializer=lambda x: json.dumps(x).encode("utf-8"),
    )

    log.info("ML2 Kafka loop started — listening to agent-findings...")

    while True:
        records = await asyncio.to_thread(consumer.poll, 100)
        if not records:
            continue

        for _, messages in records.items():
            for msg in messages:
                payload = msg.value
                case_id = payload.get("case_id")
                try:
                    log.info("[%s] received from agent-findings", case_id)
                    narrative_report = await asyncio.to_thread(main_pipeline, payload)

                    verified_payload = {
                        "case_id":            case_id,
                        "verified_facts":     narrative_report.get("verified_facts", []),
                        "inferences":         narrative_report.get("inferences", []),
                        "counter_arguments":  narrative_report.get("counter_arguments", []),
                        "revised_confidence": narrative_report.get("revised_confidence", 0.0),
                        "hallucination_rate": narrative_report.get("hallucination_rate", 0.0),
                        "narrative_md":       narrative_report.get("narrative_md", ""),
                    }

                    await asyncio.to_thread(producer.send, "ml2-verified-findings", verified_payload)
                    await asyncio.to_thread(producer.flush)
                    await inst.set(
                        f"pipeline:{case_id}:state",
                        json.dumps({"step": "ml2_complete", "status": "done"}),
                        ex=86400,
                    )
                    log.info("[%s] pushed | confidence=%.3f", case_id, verified_payload["revised_confidence"])
                except Exception as exc:
                    log.error("[%s] Failed: %s", case_id, exc)

if __name__ == "__main__":

    if MODE == "kafka":

        asyncio.run(kafka_loop())

    else:

        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT", 8001)),
            reload=os.getenv("ENV", "dev") == "dev",
        )
