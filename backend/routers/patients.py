# routers/patients.py — CRUD de Pacientes con RBAC, soft-delete y cifrado AES-256
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from uuid import UUID

from database import get_db
from models import User, Patient, RiskReport, ModelFeedback
from schemas import PatientCreate, PatientResponse, PatientUpdate, SignReportRequest
from auth import get_current_user, require_admin, require_medico_or_admin, log_audit
from encryption import encrypt_field, decrypt_field

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


@router.get("/pending-reports")
def list_pending_reports(
    current_user: User = Depends(require_medico_or_admin),
    db: Session = Depends(get_db),
):
    """Lista reportes de riesgo pendientes de firma para el médico actual."""
    query = db.query(RiskReport).filter(
        RiskReport.signed_at.is_(None),
        RiskReport.deleted_at.is_(None),
    )

    # Si es médico, solo mostrar reportes de sus pacientes asignados
    if current_user.role == "medico":
        patient_ids = db.query(Patient.id).filter(
            Patient.assigned_doctor_id == current_user.id,
            Patient.deleted_at.is_(None),
        ).subquery()
        query = query.filter(RiskReport.patient_id.in_(patient_ids))

    reports = query.order_by(RiskReport.created_at.desc()).all()

    # Obtener nombres de pacientes
    patient_names = {}
    for r in reports:
        if str(r.patient_id) not in patient_names:
            p = db.query(Patient).filter(Patient.id == r.patient_id).first()
            patient_names[str(r.patient_id)] = p.name if p else "Desconocido"

    return {
        "total": len(reports),
        "data": [
            {
                "id": str(r.id),
                "patient_id": str(r.patient_id),
                "patient_name": patient_names.get(str(r.patient_id), ""),
                "model_type": r.model_type,
                "risk_score": r.risk_score,
                "risk_category": r.risk_category,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
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

    # No auditar listados — generan demasiado ruido

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
                # Datos sensibles descifrados solo para médico asignado o admin
                "identification_doc": decrypt_field(p.identification_doc) if current_user.role in ("admin", "medico") else "Oculto",
                "medical_summary": decrypt_field(p.medical_summary) if current_user.role == "medico" else None,
            }
            for p in patients
        ],
    }


# ──────────────────────────────────────────
# RISK REPORTS DE UN PACIENTE
# ──────────────────────────────────────────
@router.get("/{patient_id}/risk-reports")
def list_risk_reports(
    patient_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista los RiskReports de un paciente."""
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.deleted_at.is_(None),
    ).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # RBAC
    if current_user.role == "paciente" and patient.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este paciente")
    if current_user.role == "medico" and patient.assigned_doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Este paciente no está asignado a ti")

    reports = db.query(RiskReport).filter(
        RiskReport.patient_id == patient_id,
        RiskReport.deleted_at.is_(None),
    ).order_by(RiskReport.created_at.desc()).all()

    return {
        "total": len(reports),
        "data": [
            {
                "id": str(r.id),
                "patient_id": str(r.patient_id),
                "model_type": r.model_type,
                "risk_score": r.risk_score,
                "risk_category": r.risk_category,
                "risk_prediction": r.risk_prediction,
                "shap_values": r.shap_values,
                "signed_by": str(r.signed_by) if r.signed_by else None,
                "signed_at": r.signed_at.isoformat() if r.signed_at else None,
                "clinical_notes": r.clinical_notes,
                "feedback": r.feedback,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
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

    # No auditar vistas individuales — generan demasiado ruido

    return {
        "id": str(patient.id),
        "name": patient.name,
        "birth_date": patient.birth_date,
        "gender": patient.gender,
        "identification_doc": decrypt_field(patient.identification_doc),
        "medical_summary": decrypt_field(patient.medical_summary),
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
    """Crear nuevo paciente. Campos sensibles se cifran con AES-256."""
    patient = Patient(
        name=body.name,
        birth_date=body.birth_date,
        gender=body.gender,
        identification_doc=encrypt_field(body.identification_doc),
        medical_summary=encrypt_field(body.medical_summary),
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
    # Cifrar campos sensibles si se actualizan
    encrypted_fields = {"identification_doc", "medical_summary"}
    for key, value in update_data.items():
        if key in encrypted_fields:
            value = encrypt_field(value)
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


# ──────────────────────────────────────────
# FIRMA DE RISK REPORT (Paso 7 del flujo clínico)
# ──────────────────────────────────────────
@router.patch("/{patient_id}/risk-reports/{report_id}/sign")
def sign_risk_report(
    patient_id: UUID,
    report_id: UUID,
    body: SignReportRequest,
    current_user: User = Depends(require_medico_or_admin),
    db: Session = Depends(get_db),
):
    """
    Paso 7: Firma obligatoria del RiskReport.
    - Médico escribe observaciones clínicas (>= 30 chars).
    - Selecciona ACCEPT o REJECT.
    - Si REJECT: justificación >= 20 chars.
    - Actualiza signed_by y signed_at en BD y FHIR.
    - Retroalimentación guardada en model_feedback.
    Audit log: SIGN_REPORT.
    """
    # Verificar que el reporte existe y pertenece al paciente
    report = db.query(RiskReport).filter(
        RiskReport.id == report_id,
        RiskReport.patient_id == patient_id,
        RiskReport.deleted_at.is_(None),
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="RiskReport no encontrado para este paciente")

    # Verificar que no esté ya firmado
    if report.signed_at is not None:
        raise HTTPException(status_code=409, detail="Este reporte ya fue firmado")

    # Validar justificación si rechaza
    if body.action == "REJECT":
        if not body.justification or len(body.justification) < 20:
            raise HTTPException(
                status_code=400,
                detail="Si rechaza el reporte, debe proporcionar una justificación de al menos 20 caracteres",
            )

    # Firmar el reporte
    report.signed_by = current_user.id
    report.signed_at = datetime.now(timezone.utc)
    report.clinical_notes = body.clinical_notes
    report.feedback = body.action

    # Guardar feedback en model_feedback
    feedback_entry = ModelFeedback(
        risk_report_id=report.id,
        doctor_id=current_user.id,
        action=body.action,
        justification=body.justification if body.action == "REJECT" else body.clinical_notes,
    )
    db.add(feedback_entry)
    db.commit()

    # Audit log
    log_audit(
        db, current_user.id, "SIGN_REPORT", "RiskReport",
        str(report_id),
        details={
            "patient_id": str(patient_id),
            "action": body.action,
            "model_type": report.model_type,
        },
    )

    return {
        "message": f"RiskReport {'aceptado' if body.action == 'ACCEPT' else 'rechazado'} y firmado",
        "report_id": str(report_id),
        "signed_by": str(current_user.id),
        "signed_at": report.signed_at.isoformat(),
        "action": body.action,
    }


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
