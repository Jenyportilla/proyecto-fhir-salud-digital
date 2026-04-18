# routers/inference.py — Endpoints de inferencia ML/DL via Orquestador
# Proxy al orchestrator + crea RiskReport cuando la inferencia finaliza

import os
import httpx
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Patient, RiskReport, InferenceQueue, AuditLog
from auth import get_current_user, require_medico_or_admin, User
from schemas import InferenceMLRequest, InferenceDLRequest

router = APIRouter(prefix="/inference", tags=["Inference"])

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8003")


def log_audit(db, user_id, action, resource_type, resource_id=None):
    entry = AuditLog(user_id=user_id, action=action, resource_type=resource_type, resource_id=resource_id)
    db.add(entry)
    db.commit()


@router.post("/ml")
async def run_ml_inference(
    body: InferenceMLRequest,
    current_user: User = Depends(require_medico_or_admin),
    db: Session = Depends(get_db),
):
    """Lanzar inferencia ML tabular para un paciente."""
    # Verificar que el paciente existe
    patient = db.query(Patient).filter(
        Patient.id == body.patient_id,
        Patient.deleted_at.is_(None),
    ).first()
    if not patient:
        raise HTTPException(404, "Paciente no encontrado")

    # Llamar al orquestador
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{ORCHESTRATOR_URL}/infer", json={
                "patient_id": str(body.patient_id),
                "model_type": "ML",
                "features": body.features,
            })
            resp.raise_for_status()
            result = resp.json()
    except Exception as e:
        raise HTTPException(503, f"Orquestador no disponible: {e}")

    # Registrar en cola de inferencia
    queue_entry = InferenceQueue(
        task_id=result["task_id"],
        patient_id=body.patient_id,
        model_type="ML",
        status="PENDING",
    )
    db.add(queue_entry)
    db.commit()

    log_audit(db, current_user.id, "INFERENCE_ML", "InferenceQueue", result["task_id"])

    return {"task_id": result["task_id"], "status": "PENDING", "model_type": "ML"}


@router.post("/dl")
async def run_dl_inference(
    body: InferenceDLRequest,
    current_user: User = Depends(require_medico_or_admin),
    db: Session = Depends(get_db),
):
    """Lanzar inferencia DL de imagen para un paciente."""
    patient = db.query(Patient).filter(
        Patient.id == body.patient_id,
        Patient.deleted_at.is_(None),
    ).first()
    if not patient:
        raise HTTPException(404, "Paciente no encontrado")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{ORCHESTRATOR_URL}/infer", json={
                "patient_id": str(body.patient_id),
                "model_type": "DL",
                "image_url": body.image_url,
            })
            resp.raise_for_status()
            result = resp.json()
    except Exception as e:
        raise HTTPException(503, f"Orquestador no disponible: {e}")

    queue_entry = InferenceQueue(
        task_id=result["task_id"],
        patient_id=body.patient_id,
        model_type="DL",
        status="PENDING",
    )
    db.add(queue_entry)
    db.commit()

    log_audit(db, current_user.id, "INFERENCE_DL", "InferenceQueue", result["task_id"])

    return {"task_id": result["task_id"], "status": "PENDING", "model_type": "DL"}


@router.get("/status/{task_id}")
async def get_inference_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Consultar estado de una inferencia. Si está DONE, crea el RiskReport."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{ORCHESTRATOR_URL}/status/{task_id}")
            resp.raise_for_status()
            task_data = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(404, "Task no encontrada")
        raise HTTPException(503, f"Orquestador no disponible")
    except Exception:
        raise HTTPException(503, "Orquestador no disponible")

    # Actualizar estado en BD local
    queue_entry = db.query(InferenceQueue).filter(
        InferenceQueue.task_id == task_id
    ).first()

    if queue_entry and task_data["status"] != queue_entry.status:
        queue_entry.status = task_data["status"]
        if task_data.get("result"):
            queue_entry.result = task_data["result"]
        if task_data.get("error"):
            queue_entry.error_msg = task_data["error"]

        # Si está DONE, crear RiskReport
        if task_data["status"] == "DONE" and task_data.get("result"):
            result = task_data["result"]
            existing = db.query(RiskReport).filter(
                RiskReport.patient_id == queue_entry.patient_id,
                RiskReport.model_type == queue_entry.model_type,
                RiskReport.deleted_at.is_(None),
            ).first()

            if not existing:
                report = RiskReport(
                    patient_id=queue_entry.patient_id,
                    model_type=queue_entry.model_type,
                    risk_score=result.get("probability") or result.get("risk_score"),
                    risk_category=result.get("risk_category", "MEDIUM"),
                    risk_prediction=result.get("risk_prediction"),
                    shap_values=result.get("shap_values"),
                    gradcam_url=result.get("gradcam_url"),
                )
                db.add(report)
                log_audit(db, current_user.id, "CREATE_RISK_REPORT", "RiskReport", str(report.id))

        db.commit()

    return task_data
