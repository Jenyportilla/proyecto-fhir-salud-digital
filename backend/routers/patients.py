# routers/patients.py — CRUD de Pacientes con RBAC y soft-delete
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from uuid import UUID

from database import get_db
from models import User, Patient, RiskReport
from schemas import PatientCreate, PatientResponse, PatientUpdate
from auth import get_current_user, require_admin, require_medico_or_admin, log_audit

router = APIRouter(prefix="/fhir/Patient", tags=["Pacientes (FHIR Patient)"])


@router.get("/doctors")
def list_doctors(
    current_user: User = Depends(require_medico_or_admin),
    db: Session = Depends(get_db),
):
    """Lista medicos activos para asignacion de pacientes."""
    doctors = db.query(User).filter(
        User.role == "medico",
        User.is_active == True,
        User.deleted_at.is_(None),
    ).all()

    return {
        "data": [
            {
                "id": str(d.id),
                "full_name": d.full_name,
                "email": d.email,
            }
            for d in doctors
        ],
    }



@router.get("")
def list_patients(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lista paginada de pacientes (Paso 2 del flujo clínico).
    - Admin: ve todos
    - Médico: ve solo los asignados
    - Paciente: ve solo el propio
    """
    query = db.query(Patient).filter(Patient.deleted_at.is_(None))

    if current_user.role == "medico":
        query = query.filter(Patient.assigned_doctor_id == current_user.id)
    elif current_user.role == "paciente":
        query = query.filter(Patient.owner_id == current_user.id)

    total = query.count()
    patients = query.order_by(Patient.created_at.desc()).offset(offset).limit(limit).all()

    log_audit(db, current_user.id, "LIST_PATIENTS", "Patient")

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [
            {
                "id": str(p.id),
                "name": p.name,
                "birth_date": p.birth_date,
                "gender": p.gender,
                "status": p.status,
                "assigned_doctor_id": str(p.assigned_doctor_id) if p.assigned_doctor_id else None,
                "assigned_doctor_name": p.assigned_doctor.full_name if p.assigned_doctor else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                # Datos sensibles solo para médico asignado o admin
                "identification_doc": p.identification_doc if current_user.role in ("admin", "medico") else "Oculto",
                "medical_summary": p.medical_summary if current_user.role == "medico" else None,
            }
            for p in patients
        ],
    }


@router.get("/{patient_id}")
def get_patient(
    patient_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Detalle de un paciente (Paso 3 del flujo clínico)."""
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.deleted_at.is_(None),
    ).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # RBAC: Paciente solo ve el propio
    if current_user.role == "paciente" and patient.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este paciente")
    # Médico solo ve asignados
    if current_user.role == "medico" and patient.assigned_doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Este paciente no está asignado a ti")

    log_audit(db, current_user.id, "VIEW_PATIENT", "Patient", str(patient_id))

    return {
        "id": str(patient.id),
        "name": patient.name,
        "birth_date": patient.birth_date,
        "gender": patient.gender,
        "identification_doc": patient.identification_doc,
        "medical_summary": patient.medical_summary,
        "status": patient.status,
        "assigned_doctor_id": str(patient.assigned_doctor_id) if patient.assigned_doctor_id else None,
        "assigned_doctor_name": patient.assigned_doctor.full_name if patient.assigned_doctor else None,
        "created_at": patient.created_at.isoformat() if patient.created_at else None,
        "updated_at": patient.updated_at.isoformat() if patient.updated_at else None,
    }


@router.post("", status_code=201)
def create_patient(
    body: PatientCreate,
    current_user: User = Depends(require_medico_or_admin),
    db: Session = Depends(get_db),
):
    """Crear nuevo paciente."""
    patient = Patient(
        name=body.name,
        birth_date=body.birth_date,
        gender=body.gender,
        identification_doc=body.identification_doc,
        medical_summary=body.medical_summary,
        assigned_doctor_id=body.assigned_doctor_id or (
            current_user.id if current_user.role == "medico" else None
        ),
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    log_audit(db, current_user.id, "CREATE_PATIENT", "Patient", str(patient.id))

    return {"message": "Paciente creado", "id": str(patient.id)}


@router.patch("/{patient_id}")
def update_patient(
    patient_id: UUID,
    body: PatientUpdate,
    current_user: User = Depends(require_medico_or_admin),
    db: Session = Depends(get_db),
):
    """Actualizar datos de un paciente."""
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.deleted_at.is_(None),
    ).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(patient, key, value)

    db.commit()
    log_audit(db, current_user.id, "UPDATE_PATIENT", "Patient", str(patient_id))

    return {"message": "Paciente actualizado", "id": str(patient_id)}


@router.delete("/{patient_id}")
def delete_patient(
    patient_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Soft-delete de paciente (solo Admin)."""
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.deleted_at.is_(None),
    ).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    patient.deleted_at = datetime.now(timezone.utc)
    db.commit()

    log_audit(db, current_user.id, "DELETE_PATIENT", "Patient", str(patient_id))

    return {"message": "Paciente eliminado (soft-delete)", "id": str(patient_id)}


@router.patch("/{patient_id}/restore")
def restore_patient(
    patient_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Restaurar paciente eliminado (solo Admin)."""
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.deleted_at.isnot(None),
    ).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado o no está eliminado")

    patient.deleted_at = None
    db.commit()

    log_audit(db, current_user.id, "RESTORE_PATIENT", "Patient", str(patient_id))

    return {"message": "Paciente restaurado", "id": str(patient_id)}


@router.get("/{patient_id}/can-close")
def can_close_patient(
    patient_id: UUID,
    current_user: User = Depends(require_medico_or_admin),
    db: Session = Depends(get_db),
):
    """
    Paso 8: Verifica si el paciente puede ser cerrado.
    No se puede cerrar si tiene RiskReports sin firma.
    """
    pending = db.query(RiskReport).filter(
        RiskReport.patient_id == patient_id,
        RiskReport.signed_at.is_(None),
        RiskReport.deleted_at.is_(None),
    ).count()

    if pending > 0:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "PENDING_SIGNATURE",
                "message": "Debe firmar el RiskReport antes de cerrar el paciente",
                "pending_count": pending,
            },
        )

    log_audit(db, current_user.id, "CLOSE_PATIENT", "Patient", str(patient_id))

    return {"can_close": True, "message": "Paciente puede ser cerrado"}
