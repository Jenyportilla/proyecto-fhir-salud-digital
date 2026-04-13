# auth.py — Autenticación JWT + doble API-Key + RBAC
# Proyecto FHIR Salud Digital (C2)

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models import User, AuditLog

# ──────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────
SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-jwt-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8

# Bcrypt con work factor 12
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# Bearer token scheme
security = HTTPBearer(auto_error=False)


# ──────────────────────────────────────────
# PASSWORD HASHING
# ──────────────────────────────────────────
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ──────────────────────────────────────────
# JWT TOKENS
# ──────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


# ──────────────────────────────────────────
# DOBLE API-KEY VALIDATION
# ──────────────────────────────────────────
def validate_api_keys(
    x_access_key: str = Header(..., alias="X-Access-Key"),
    x_permission_key: str = Header(..., alias="X-Permission-Key"),
):
    """Valida las dos API Keys como primera capa de autenticación."""
    valid_access = os.getenv("ACCESS_KEY", "master-access-key")

    if x_access_key != valid_access:
        raise HTTPException(status_code=401, detail="X-Access-Key inválido")

    valid_permissions = {
        os.getenv("ADMIN_PERM_KEY", "admin-permission"): "admin",
        os.getenv("MEDICO_PERM_KEY", "medico-permission"): "medico",
        os.getenv("PACIENTE_PERM_KEY", "paciente-permission"): "paciente",
    }

    if x_permission_key not in valid_permissions:
        raise HTTPException(status_code=403, detail="X-Permission-Key inválido")

    return valid_permissions[x_permission_key]


# ──────────────────────────────────────────
# GET CURRENT USER (JWT)
# ──────────────────────────────────────────
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Extrae el usuario actual del JWT Bearer token."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Token de autenticación requerido")

    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(status_code=401, detail="Token inválido: sin user_id")

    user = db.query(User).filter(
        User.id == UUID(user_id),
        User.deleted_at.is_(None),
        User.is_active.is_(True),
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")

    return user


# ──────────────────────────────────────────
# RBAC DECORADORES
# ──────────────────────────────────────────
def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Solo permite acceso a usuarios con rol admin."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado: se requiere rol admin")
    return current_user


def require_medico(current_user: User = Depends(get_current_user)) -> User:
    """Solo permite acceso a usuarios con rol medico."""
    if current_user.role != "medico":
        raise HTTPException(status_code=403, detail="Acceso denegado: se requiere rol médico")
    return current_user


def require_medico_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """Permite acceso a médicos y admins."""
    if current_user.role not in ("admin", "medico"):
        raise HTTPException(status_code=403, detail="Acceso denegado: se requiere rol médico o admin")
    return current_user


# ──────────────────────────────────────────
# AUDIT LOG HELPER
# ──────────────────────────────────────────
def log_audit(
    db: Session,
    user_id,
    action: str,
    resource_type: str = None,
    resource_id: str = None,
    status: str = "SUCCESS",
    details: dict = None,
    ip_address: str = None,
):
    """Registra una acción en el audit log (INSERT-ONLY)."""
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        status=status,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
