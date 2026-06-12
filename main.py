import uvicorn
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Optional

import redis
import json

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse

from flow.src.task_run_pipelines import task_run_pipelines

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))

LOGS_DIR = DATA_DIR / "logs"

DUMPS_DIR = DATA_DIR / "m_dumps"

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")

REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

REDIS_DB = int(os.getenv("REDIS_DB", 0))

ASYNC_MODE = os.getenv("ASYNC_MODE", "false").lower() == "true"

LOGS_DIR.mkdir(parents=True, exist_ok=True)

DUMPS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("main")
app = FastAPI(
    title="Iron Hand — ML1 Incident Response API",
    description=(
        "Autonomous incident response: upload memory dumps or log files "
        "and receive ML-scored threat analysis. BE2 not required."
    ),
    version="1.0.0",
)

def _redis() -> redis.Redis:

    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)



def _save_upload(upload: UploadFile, dest_dir: Path, case_id: str) -> Path:

    suffix = Path(upload.filename).suffix if upload.filename else ".bin"

    dest = dest_dir / f"{case_id}{suffix}"

    with open(dest, "wb") as f:

        f.write(upload.file.read())

    logger.info("Saved upload → %s (%d bytes)", dest, dest.stat().st_size)

    return dest


def _run_and_store(job: dict) -> dict:

    results = task_run_pipelines.fn(jobs=[job])

    result = results[0] if results else {"case_id": job["case_id"], "status": "error", "error": "no result"}

    return result


def _store_redis(case_id: str, payload: dict, ttl: int = 3600) -> None:

    try:

        _redis().setex(f"ml1:result:{case_id}", ttl, json.dumps(payload))

    except redis.RedisError as exc:

        logger.warning("Redis store failed for %s: %s", case_id, exc)


def _get_redis(case_id: str) -> Optional[dict]:

    try:

        raw = _redis().get(f"ml1:result:{case_id}")

        return json.loads(raw) if raw else None

    except redis.RedisError:

        return None

def _background_run(job: dict) -> None:

    result = _run_and_store(job)

    _store_redis(job["case_id"], result)

@app.get("/health")
def health():

    redis_ok = True

    try:

        _redis().ping()

    except Exception:

        redis_ok = False

    return {"status": "ok", "redis": redis_ok, "async_mode": ASYNC_MODE}


@app.post("/analyze/logs")
async def analyze_logs(
    background_tasks: BackgroundTasks,
    log_file: UploadFile = File(..., description="Event log file (.evtx, .log, .csv)"),
    case_id: Optional[str] = Form(default=None, description="Optional case ID; auto-generated if omitted"),
):

    case_id = case_id or str(uuid.uuid4())

    log_path = str(_save_upload(log_file, LOGS_DIR, case_id))

    job = {
        "case_id": case_id,
        "log_path": log_path,
        "mode": "predict",
    }

    if ASYNC_MODE:

        background_tasks.add_task(_background_run, job)

        return JSONResponse({"case_id": case_id, "status": "processing", "poll": f"/result/{case_id}"})

    result = _run_and_store(job)

    _store_redis(case_id, result)

    return JSONResponse(result)


@app.post("/analyze/memory")
async def analyze_memory(
    background_tasks: BackgroundTasks,
    dump_file: UploadFile = File(..., description="Memory dump file (.raw, .dmp, .mem)"),
    case_id: Optional[str] = Form(default=None),
    labels_json: Optional[str] = Form(default=None, description='JSON array of labels, e.g. ["clean","infected"]'),
):

    case_id = case_id or str(uuid.uuid4())

    dump_path = str(_save_upload(dump_file, DUMPS_DIR, case_id))

    labels = []

    if labels_json:

        try:

            labels = json.loads(labels_json)

        except json.JSONDecodeError:

            raise HTTPException(status_code=422, detail="labels_json must be a valid JSON array")

    job = {
        "case_id": case_id,
        "log_path": "",
        "memory_dump_path": dump_path,
        "parsed_memory_cases": None,
        "labels": labels or None,
        "mode": "predict",
    }

    if ASYNC_MODE:

        background_tasks.add_task(_background_run, job)

        return JSONResponse({"case_id": case_id, "status": "processing", "poll": f"/result/{case_id}"})

    result = _run_and_store(job)

    _store_redis(case_id, result)

    return JSONResponse(result)


@app.post("/analyze/full")
async def analyze_full(
    background_tasks: BackgroundTasks,
    log_file: Optional[UploadFile] = File(default=None, description="Log file (optional)"),
    dump_file: Optional[UploadFile] = File(default=None, description="Memory dump (optional)"),
    case_id: Optional[str] = Form(default=None),
    labels_json: Optional[str] = Form(default=None),
):

    if log_file is None and dump_file is None:

        raise HTTPException(status_code=422, detail="Provide at least one file: log_file or dump_file")

    case_id = case_id or str(uuid.uuid4())

    log_path = str(_save_upload(log_file, LOGS_DIR, case_id)) if log_file else ""

    dump_path = str(_save_upload(dump_file, DUMPS_DIR, case_id)) if dump_file else ""

    labels = []

    if labels_json:

        try:

            labels = json.loads(labels_json)

        except json.JSONDecodeError:

            raise HTTPException(status_code=422, detail="labels_json must be a valid JSON array")

    job = {
        "case_id": case_id,
        "log_path": log_path,
        "memory_dump_path": dump_path,
        "parsed_memory_cases": None,
        "labels": labels or None,
        "mode": "predict",
    }

    if ASYNC_MODE:

        background_tasks.add_task(_background_run, job)

        return JSONResponse({"case_id": case_id, "status": "processing", "poll": f"/result/{case_id}"})

    result = _run_and_store(job)

    _store_redis(case_id, result)

    return JSONResponse(result)


@app.get("/result/{case_id}")
def get_result(case_id: str):

    result = _get_redis(case_id)

    if result is None:

        raise HTTPException(status_code=404, detail=f"No result found for case_id={case_id}")

    status_code = 202 if result.get("status") == "processing" else 200

    return JSONResponse(result, status_code=status_code)


@app.post("/train/logs")
async def train_logs(
    log_file: UploadFile = File(...),
    y_train_json: str = Form(..., description='JSON array of labels, e.g. [0, 1, 0, 1]'),
    case_id: Optional[str] = Form(default=None),
):

    case_id = case_id or str(uuid.uuid4())

    log_path = str(_save_upload(log_file, LOGS_DIR, case_id))

    try:

        y_train = json.loads(y_train_json)

    except json.JSONDecodeError:

        raise HTTPException(status_code=422, detail="y_train_json must be a valid JSON array")

    job = {
        "case_id": case_id,
        "log_path": log_path,
        "y_train": y_train,
        "mode": "train",
    }

    result = _run_and_store(job)

    return JSONResponse(result)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENV", "dev") == "dev",
        log_level="info",
    )