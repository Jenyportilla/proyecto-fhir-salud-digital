# routers/admin.py — Panel de administración: usuarios, audit log, estadísticas
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
from uuid import UUID

from database import get_db
from models import User, Patient, Observation, RiskReport, AuditLog
from schemas import UserCreate, UserResponse, UserUpdate, AuditLogResponse
from auth import require_admin, hash_password, log_audit

router = APIRouter(prefix="/admin", tags=["Admin"])


# ──────────────────────────────────────────
# GESTIÓN DE USUARIOS
# ──────────────────────────────────────────
@router.get("/users")
def list_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Lista todos los usuarios (solo Admin)."""
    query = db.query(User).filter(User.deleted_at.is_(None))
    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "identification_doc": u.identification_doc,
                "role": u.role,
                "is_active": u.is_active,
                "habeas_data_accepted": u.habeas_data_accepted,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "updated_at": u.updated_at.isoformat() if u.updated_at else None,
            }
            for u in users
        ],
    }


@router.post("/users", status_code=201)
def create_user(
    body: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Crear nuevo usuario (solo Admin)."""
    # Verificar email duplicado
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email ya registrado")

    # Verificar cedula duplicada
    existing_doc = db.query(User).filter(User.identification_doc == body.identification_doc).first()
    if existing_doc:
        raise HTTPException(status_code=409, detail="Cedula ya registrada")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        identification_doc=body.identification_doc,
        role=body.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_audit(db, current_user.id, "CREATE_USER", "User", str(user.id))

    return {"message": "Usuario creado", "id": str(user.id)}


@router.patch("/users/{user_id}")
def update_user(
    user_id: UUID,
    body: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Actualizar usuario (solo Admin)."""
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    log_audit(db, current_user.id, "UPDATE_USER", "User", str(user_id))

    return {"message": "Usuario actualizado", "id": str(user_id)}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Soft-delete de usuario (solo Admin)."""
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")

    user.deleted_at = datetime.now(timezone.utc)
    user.is_active = False
    db.commit()

    log_audit(db, current_user.id, "DELETE_USER", "User", str(user_id))

    return {"message": "Usuario eliminado (soft-delete)", "id": str(user_id)}


# ──────────────────────────────────────────
# LISTAR MEDICOS (para asignacion)
# ──────────────────────────────────────────
@router.get("/doctors")
def list_doctors(
    current_user: User = Depends(require_admin),
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


# ──────────────────────────────────────────
# AUDIT LOG
# ──────────────────────────────────────────
@router.get("/audit-log")
def list_audit_log(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: str = Query(None, description="Filtrar por acción (LOGIN, LOGOUT, etc.)"),
    user_id: str = Query(None, description="Filtrar por ID de usuario"),
    resource_type: str = Query(None, description="Filtrar por tipo de recurso (Patient, User, etc.)"),
    date_from: str = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    date_to: str = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Ver audit log (solo Admin). Filtrable por acción, usuario, recurso y fechas.
    También como FHIR AuditEvent.
    """
    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == UUID(user_id))
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if date_from:
        from datetime import datetime as dt
        query = query.filter(AuditLog.timestamp >= dt.fromisoformat(date_from))
    if date_to:
        from datetime import datetime as dt
        query = query.filter(AuditLog.timestamp <= dt.fromisoformat(date_to + "T23:59:59"))

    total = query.count()
    entries = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    # Obtener nombres de usuarios
    user_ids = {e.user_id for e in entries if e.user_id}
    user_map = {}
    if user_ids:
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        user_map = {u.id: {"name": u.full_name, "email": u.email} for u in users}

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [
            {
                "id": str(e.id),
                "user_id": str(e.user_id) if e.user_id else None,
                "user_name": user_map.get(e.user_id, {}).get("name", "Desconocido"),
                "user_email": user_map.get(e.user_id, {}).get("email", ""),
                "action": e.action,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "status": e.status,
                "details": e.details,
                "ip_address": e.ip_address,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            }
            for e in entries
        ],
    }


@router.get("/audit-log/export")
def export_audit_log(
    format: str = Query("json", description="Formato de exportación: json o csv"),
    action: str = Query(None),
    user_id: str = Query(None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Exportar audit log en formato JSON o CSV (solo Admin)."""
    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == UUID(user_id))

    entries = query.order_by(AuditLog.timestamp.desc()).all()

    data = [
        {
            "id": str(e.id),
            "user_id": str(e.user_id) if e.user_id else None,
            "action": e.action,
            "resource_type": e.resource_type,
            "resource_id": e.resource_id,
            "status": e.status,
            "ip_address": e.ip_address,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        }
        for e in entries
    ]

    if format.lower() == "csv":
        import csv
        import io
        from fastapi.responses import StreamingResponse

        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
        )

    return {"total": len(data), "data": data}


# ──────────────────────────────────────────
# ESTADÍSTICAS
# ──────────────────────────────────────────
@router.get("/stats")
def get_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Estadísticas generales del sistema (solo Admin)."""
    return {
        "users": {
            "total": db.query(User).filter(User.deleted_at.is_(None)).count(),
            "admins": db.query(User).filter(User.role == "admin", User.deleted_at.is_(None)).count(),
            "medicos": db.query(User).filter(User.role == "medico", User.deleted_at.is_(None)).count(),
            "pacientes": db.query(User).filter(User.role == "paciente", User.deleted_at.is_(None)).count(),
        },
        "patients": {
            "total": db.query(Patient).filter(Patient.deleted_at.is_(None)).count(),
            "active": db.query(Patient).filter(Patient.status == "active", Patient.deleted_at.is_(None)).count(),
        },
        "observations": {
            "total": db.query(Observation).filter(Observation.deleted_at.is_(None)).count(),
        },
        "risk_reports": {
            "total": db.query(RiskReport).filter(RiskReport.deleted_at.is_(None)).count(),
            "pending_signature": db.query(RiskReport).filter(
                RiskReport.signed_at.is_(None), RiskReport.deleted_at.is_(None)
            ).count(),
        },
        "audit_log": {
            "total_entries": db.query(AuditLog).count(),
        },
    }
