# routers/observations.py — CRUD de Observaciones con LOINC
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from uuid import UUID

from database import get_db
from models import User, Patient, Observation
from schemas import ObservationCreate, ObservationResponse
from auth import get_current_user, require_medico_or_admin, require_admin, log_audit

router = APIRouter(prefix="/fhir/Observation", tags=["Observaciones (FHIR Observation)"])

# Códigos LOINC válidos para validación
VALID_LOINC = {
    "2339-0":  "Glucosa [Mass/volume] in Blood",
    "55284-4": "Blood pressure systolic and diastolic",
    "39156-5": "Body mass index (BMI)",
    "14749-6": "Insulin [Units/volume] in Serum",
    "8310-5":  "Body temperature",
    "8867-4":  "Heart rate",
    "2345-7":  "Glucose [Mass/volume] in Serum",
    "718-7":   "Hemoglobin [Mass/volume] in Blood",
    "2160-0":  "Creatinine [Mass/volume] in Serum",
    "6690-2":  "Leukocytes [#/volume] in Blood",
}

# Rangos para detección de outliers
OUTLIER_RANGES = {
    "8310-5":  {"min": 30, "max": 45, "label": "Temperatura"},       # °C
    "8867-4":  {"min": 20, "max": 250, "label": "Frecuencia Cardíaca"}, # lpm
    "55284-4": {"min": 40, "max": 300, "label": "Presión Arterial"},  # mmHg
    "2339-0":  {"min": 20, "max": 600, "label": "Glucosa"},           # mg/dL
}


@router.get("")
def list_observations(
    patient_id: UUID = Query(None, description="Filtrar por paciente"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista observaciones con paginación, filtro por paciente y RBAC."""
    query = db.query(Observation).filter(Observation.deleted_at.is_(None))

    if patient_id:
        query = query.filter(Observation.patient_id == patient_id)

    # Si es paciente, solo ve sus propias observaciones
    if current_user.role == "paciente":
        patient_ids = db.query(Patient.id).filter(
            Patient.owner_id == current_user.id,
            Patient.deleted_at.is_(None),
        ).subquery()
        query = query.filter(Observation.patient_id.in_(patient_ids))
    elif current_user.role == "medico":
        patient_ids = db.query(Patient.id).filter(
            Patient.assigned_doctor_id == current_user.id,
            Patient.deleted_at.is_(None),
        ).subquery()
        query = query.filter(Observation.patient_id.in_(patient_ids))

    total = query.count()
    observations = query.order_by(Observation.effective_date.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [
            {
                "id": str(o.id),
                "patient_id": str(o.patient_id),
                "loinc_code": o.loinc_code,
                "loinc_display": o.loinc_display,
                "value": o.value,
                "unit": o.unit,
                "effective_date": o.effective_date.isoformat() if o.effective_date else None,
                "is_outlier": _check_outlier(o.loinc_code, o.value),
            }
            for o in observations
        ],
    }


@router.post("", status_code=201)
def create_observation(
    body: ObservationCreate,
    current_user: User = Depends(require_medico_or_admin),
    db: Session = Depends(get_db),
):
    """Crear observación con código LOINC y validación de outliers."""
    # Verificar que el paciente existe
    patient = db.query(Patient).filter(
        Patient.id == body.patient_id,
        Patient.deleted_at.is_(None),
    ).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # Auto-completar display del LOINC
    loinc_display = body.loinc_display or VALID_LOINC.get(body.loinc_code, "")

    obs = Observation(
        patient_id=body.patient_id,
        loinc_code=body.loinc_code,
        loinc_display=loinc_display,
        value=body.value,
        unit=body.unit,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)

    log_audit(db, current_user.id, "CREATE_OBSERVATION", "Observation", str(obs.id))

    # Verificar outlier
    outlier = _check_outlier(body.loinc_code, body.value)

    return {
        "message": "Observación creada",
        "id": str(obs.id),
        "is_outlier": outlier,
        "warning": "Valor fuera de rango clinico" if outlier else None,
    }



@router.patch("/{observation_id}")
def update_observation(
    observation_id: UUID,
    body: ObservationCreate,
    current_user: User = Depends(require_medico_or_admin),
    db: Session = Depends(get_db),
):
    """Actualizar una observacion existente."""
    obs = db.query(Observation).filter(
        Observation.id == observation_id,
        Observation.deleted_at.is_(None),
    ).first()

    if not obs:
        raise HTTPException(status_code=404, detail="Observacion no encontrada")

    obs.patient_id = body.patient_id
    obs.loinc_code = body.loinc_code
    obs.loinc_display = body.loinc_display or VALID_LOINC.get(body.loinc_code, "")
    obs.value = body.value
    obs.unit = body.unit
    db.commit()

    log_audit(db, current_user.id, "UPDATE_OBSERVATION", "Observation", str(observation_id))

    return {"message": "Observacion actualizada", "id": str(observation_id)}


@router.delete("/{observation_id}")
def delete_observation(
    observation_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Soft-delete de observacion (solo Admin)."""
    obs = db.query(Observation).filter(
        Observation.id == observation_id,
        Observation.deleted_at.is_(None),
    ).first()

    if not obs:
        raise HTTPException(status_code=404, detail="Observacion no encontrada")

    obs.deleted_at = datetime.now(timezone.utc)
    db.commit()

    log_audit(db, current_user.id, "DELETE_OBSERVATION", "Observation", str(observation_id))

    return {"message": "Observacion eliminada (soft-delete)", "id": str(observation_id)}


@router.get("/outliers")
def get_outliers(
    current_user: User = Depends(require_medico_or_admin),
    db: Session = Depends(get_db),
):
    """Detectar outliers en todas las observaciones."""
    observations = db.query(Observation).filter(Observation.deleted_at.is_(None)).all()

    outliers = []
    for obs in observations:
        if _check_outlier(obs.loinc_code, obs.value):
            outliers.append({
                "id": str(obs.id),
                "patient_id": str(obs.patient_id),
                "loinc_code": obs.loinc_code,
                "loinc_display": obs.loinc_display,
                "value": obs.value,
                "unit": obs.unit,
                "range": OUTLIER_RANGES.get(obs.loinc_code, {}),
            })

    return {"total_outliers": len(outliers), "outliers": outliers}


def _check_outlier(loinc_code: str, value: float) -> bool:
    """Verifica si un valor es outlier según rangos clínicos."""
    if loinc_code in OUTLIER_RANGES:
        r = OUTLIER_RANGES[loinc_code]
        return value < r["min"] or value > r["max"]
    return False
