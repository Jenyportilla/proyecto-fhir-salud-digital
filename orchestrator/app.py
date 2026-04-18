# orchestrator/app.py — Orquestador de inferencias
# Cola concurrente: PENDING → RUNNING → DONE/ERROR
# asyncio.Semaphore(4) para limitar concurrencia

import asyncio
import uuid
import os
import httpx
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Orchestrator — Inference Queue")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config ──────────────────────────────────────────────────────
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://ml-service:8001")
DL_SERVICE_URL = os.getenv("DL_SERVICE_URL", "http://dl-service:8002")
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "4"))

semaphore = asyncio.Semaphore(MAX_CONCURRENT)

# ── In-memory task store ────────────────────────────────────────
tasks = {}


class InferRequest(BaseModel):
    patient_id: str
    model_type: str  # ML o DL
    features: Optional[dict] = None  # Para ML
    image_url: Optional[str] = None  # Para DL (URL de MinIO)


class TaskStatus(BaseModel):
    task_id: str
    status: str
    model_type: str
    patient_id: str
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


async def run_ml_inference(task_id: str, patient_id: str, features: dict):
    """Ejecuta inferencia ML en background."""
    async with semaphore:
        tasks[task_id]["status"] = "RUNNING"
        tasks[task_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {"patient_id": patient_id, **features}
                resp = await client.post(f"{ML_SERVICE_URL}/predict", json=payload)
                resp.raise_for_status()
                result = resp.json()

            tasks[task_id]["status"] = "DONE"
            tasks[task_id]["result"] = result
        except Exception as e:
            tasks[task_id]["status"] = "ERROR"
            tasks[task_id]["error"] = str(e)

        tasks[task_id]["updated_at"] = datetime.now(timezone.utc).isoformat()


async def run_dl_inference(task_id: str, patient_id: str, image_url: str):
    """Ejecuta inferencia DL en background."""
    async with semaphore:
        tasks[task_id]["status"] = "RUNNING"
        tasks[task_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

        try:
            # Descargar imagen desde MinIO/URL
            async with httpx.AsyncClient(timeout=60.0) as client:
                img_resp = await client.get(image_url)
                img_resp.raise_for_status()
                image_bytes = img_resp.content

                # Enviar al DL service como multipart
                files = {"file": ("image.png", image_bytes, "image/png")}
                data = {"patient_id": patient_id}
                resp = await client.post(
                    f"{DL_SERVICE_URL}/predict",
                    files=files,
                    data=data,
                    timeout=60.0,
                )
                resp.raise_for_status()
                result = resp.json()

            tasks[task_id]["status"] = "DONE"
            tasks[task_id]["result"] = result
        except Exception as e:
            tasks[task_id]["status"] = "ERROR"
            tasks[task_id]["error"] = str(e)

        tasks[task_id]["updated_at"] = datetime.now(timezone.utc).isoformat()


@app.post("/infer")
async def create_inference(req: InferRequest):
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    tasks[task_id] = {
        "task_id": task_id,
        "patient_id": req.patient_id,
        "model_type": req.model_type,
        "status": "PENDING",
        "result": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
    }

    if req.model_type == "ML":
        if not req.features:
            raise HTTPException(400, "features requeridos para ML")
        asyncio.create_task(run_ml_inference(task_id, req.patient_id, req.features))
    elif req.model_type == "DL":
        if not req.image_url:
            raise HTTPException(400, "image_url requerido para DL")
        asyncio.create_task(run_dl_inference(task_id, req.patient_id, req.image_url))
    else:
        raise HTTPException(400, "model_type debe ser ML o DL")

    return {"task_id": task_id, "status": "PENDING"}


@app.get("/status/{task_id}")
def get_status(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(404, "Task no encontrada")
    return task


@app.get("/tasks")
def list_tasks(limit: int = 20):
    sorted_tasks = sorted(tasks.values(), key=lambda t: t["created_at"], reverse=True)
    return {"total": len(tasks), "data": sorted_tasks[:limit]}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "orchestrator",
        "active_tasks": len([t for t in tasks.values() if t["status"] == "RUNNING"]),
        "total_tasks": len(tasks),
        "max_concurrent": MAX_CONCURRENT,
    }
