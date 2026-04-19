# routers/auth_router.py — Login, Habeas Data, gestión de sesión
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from models import User, Consent
from schemas import LoginRequest, LoginResponse, HabeasDataRequest
from auth import (
    verify_password, create_access_token, validate_api_keys,
    get_current_user, log_audit
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=LoginResponse)
def login(
    request: Request,
    body: LoginRequest,
    api_role: str = Depends(validate_api_keys),
    db: Session = Depends(get_db),
):
    """
    Login con doble API-Key + email/contraseña → JWT.
    Bloqueo tras 5 intentos fallidos (15 min).
    """
    from datetime import datetime, timezone, timedelta

    MAX_ATTEMPTS = 5
    LOCKOUT_MINUTES = 15

    user = db.query(User).filter(
        User.email == body.email.strip(),
        User.deleted_at.is_(None),
    ).first()

    # Verificar si la cuenta está bloqueada
    if user and user.locked_until:
        if datetime.now(timezone.utc) < user.locked_until:
            remaining = int((user.locked_until - datetime.now(timezone.utc)).total_seconds() // 60) + 1
            log_audit(db, None, "LOGIN", status="FAILED",
                      details={"email": body.email, "reason": "account_locked"},
                      ip_address=request.client.host)
            raise HTTPException(
                status_code=423,
                detail=f"Cuenta bloqueada por demasiados intentos fallidos. Intente en {remaining} minutos."
            )
        else:
            # Desbloquear si ya pasó el tiempo
            user.locked_until = None
            user.failed_login_attempts = 0
            db.commit()

    # Verificar cuenta activa
    if user and not user.is_active:
        raise HTTPException(status_code=401, detail="Cuenta desactivada")

    if not user or not verify_password(body.password, user.password_hash):
        # Incrementar intentos fallidos
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            remaining_attempts = MAX_ATTEMPTS - user.failed_login_attempts

            if user.failed_login_attempts >= MAX_ATTEMPTS:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
                db.commit()
                log_audit(db, user.id, "LOGIN", status="FAILED",
                          details={"email": body.email, "reason": "account_locked_max_attempts"},
                          ip_address=request.client.host)
                raise HTTPException(
                    status_code=423,
                    detail=f"Cuenta bloqueada tras {MAX_ATTEMPTS} intentos fallidos. Intente en {LOCKOUT_MINUTES} minutos."
                )

            db.commit()
            log_audit(db, user.id, "LOGIN", status="FAILED",
                      details={"email": body.email, "attempts": user.failed_login_attempts},
                      ip_address=request.client.host)
            raise HTTPException(
                status_code=401,
                detail=f"Credenciales invalidas. {remaining_attempts} intento(s) restante(s)."
            )

        log_audit(db, None, "LOGIN", status="FAILED",
                  details={"email": body.email},
                  ip_address=request.client.host)
        raise HTTPException(status_code=401, detail="Credenciales invalidas")

    # Login exitoso — resetear intentos
    user.failed_login_attempts = 0
    user.locked_until = None

    # Generar JWT
    token = create_access_token(data={
        "sub": str(user.id),
        "role": user.role,
        "email": user.email,
    })

    db.commit()

    # Audit log
    log_audit(db, user.id, "LOGIN", "User", str(user.id),
              ip_address=request.client.host)

    return LoginResponse(
        access_token=token,
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
        habeas_data_accepted=user.habeas_data_accepted,
    )


@router.post("/habeas-data")
def accept_habeas_data(
    request: Request,
    body: HabeasDataRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Aceptar consentimiento de Habeas Data (Ley 1581/2012).
    Modal obligatorio en primer login — no se puede saltar.
    """
    from datetime import datetime, timezone

    current_user.habeas_data_accepted = body.accepted
    current_user.habeas_data_timestamp = datetime.now(timezone.utc)
    current_user.habeas_data_ip = body.ip_address or request.client.host

    # Crear registro FHIR Consent
    consent = Consent(
        user_id=current_user.id,
        consent_type="habeas_data",
        version="1.0",
        accepted=body.accepted,
        ip_address=body.ip_address or request.client.host,
    )
    db.add(consent)
    db.commit()

    log_audit(db, current_user.id, "HABEAS_DATA_ACCEPTED", "Consent",
              str(consent.id), ip_address=request.client.host)

    return {"message": "Consentimiento registrado", "accepted": body.accepted}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Retorna datos del usuario autenticado."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "habeas_data_accepted": current_user.habeas_data_accepted,
    }


@router.post("/logout")
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Cerrar sesión. Registra LOGOUT en audit log.
    (El frontend debe eliminar el token JWT del almacenamiento local).
    """
    log_audit(
        db, current_user.id, "LOGOUT", "User", str(current_user.id),
        ip_address=request.client.host,
    )
    return {"message": "Sesión cerrada exitosamente"}
