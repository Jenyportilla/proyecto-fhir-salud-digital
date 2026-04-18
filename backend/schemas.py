# schemas.py — Schemas Pydantic para validación de datos entrantes/salientes
# Proyecto FHIR Salud Digital (C2)

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ──────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: UUID
    full_name: str
    habeas_data_accepted: bool

class HabeasDataRequest(BaseModel):
    accepted: bool
    ip_address: Optional[str] = None


# ──────────────────────────────────────────
# USERS
# ──────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    identification_doc: str = Field(..., min_length=5, max_length=20)
    role: str = Field(..., pattern="^(admin|medico|paciente)$")

class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    habeas_data_accepted: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    identification_doc: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


# ──────────────────────────────────────────
# PATIENTS
# ──────────────────────────────────────────
class PatientCreate(BaseModel):
    name: str = Field(..., min_length=2)
    birth_date: Optional[str] = None  # YYYY-MM-DD
    gender: Optional[str] = None
    identification_doc: str
    medical_summary: Optional[str] = None
    assigned_doctor_id: Optional[UUID] = None

class PatientResponse(BaseModel):
    id: UUID
    name: str
    birth_date: Optional[str]
    gender: Optional[str]
    identification_doc: str
    medical_summary: Optional[str]
    status: str
    assigned_doctor_id: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True

class PatientUpdate(BaseModel):
    name: Optional[str] = None
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    medical_summary: Optional[str] = None
    assigned_doctor_id: Optional[UUID] = None


# ──────────────────────────────────────────
# OBSERVATIONS
# ──────────────────────────────────────────
class ObservationCreate(BaseModel):
    patient_id: UUID
    loinc_code: str = Field(..., min_length=3)   # Ej: "2339-0"
    loinc_display: Optional[str] = None           # Ej: "Glucose"
    value: float
    unit: str = Field(..., min_length=1)           # UCUM: mg/dL, mmHg

class ObservationResponse(BaseModel):
    id: UUID
    patient_id: UUID
    loinc_code: str
    loinc_display: Optional[str]
    value: float
    unit: str
    effective_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────
# RISK REPORTS
# ──────────────────────────────────────────
class RiskReportResponse(BaseModel):
    id: UUID
    patient_id: UUID
    model_type: str
    risk_score: Optional[float]
    risk_category: Optional[str]
    risk_prediction: Optional[dict]
    shap_values: Optional[dict]
    gradcam_url: Optional[str]
    signed_by: Optional[UUID]
    signed_at: Optional[datetime]
    clinical_notes: Optional[str]
    feedback: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class SignReportRequest(BaseModel):
    clinical_notes: str = Field(..., min_length=30)
    action: str = Field(..., pattern="^(ACCEPT|REJECT)$")
    justification: Optional[str] = None  # >= 20 chars si REJECT


# ──────────────────────────────────────────
# INFERENCE
# ──────────────────────────────────────────
class InferenceRequest(BaseModel):
    patient_id: UUID
    model_type: str = Field(..., pattern="^(ML|DL)$")

class InferenceResponse(BaseModel):
    task_id: UUID
    status: str

class InferenceStatusResponse(BaseModel):
    task_id: UUID
    status: str
    result: Optional[dict] = None
    error_msg: Optional[str] = None


# ──────────────────────────────────────────
# IMÁGENES MÉDICAS
# ──────────────────────────────────────────
class ImageResponse(BaseModel):
    id: UUID
    patient_id: UUID
    original_filename: Optional[str]
    content_type: str
    modality: Optional[str]
    description: Optional[str]
    uploaded_by: Optional[UUID]
    presigned_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────
# FEEDBACK
# ──────────────────────────────────────────
class FeedbackCreate(BaseModel):
    risk_report_id: UUID
    action: str = Field(..., pattern="^(ACCEPT|REJECT)$")
    justification: Optional[str] = None  # >= 20 chars si REJECT


# ──────────────────────────────────────────
# AUDIT LOG
# ──────────────────────────────────────────
class AuditLogResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    status: str
    details: Optional[dict]
    timestamp: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────
# PAGINATION
# ──────────────────────────────────────────
class PaginatedResponse(BaseModel):
    total: int
    limit: int
    offset: int
    data: List[dict]


# ──────────────────────────────────────────
# INFERENCE
# ──────────────────────────────────────────
class InferenceMLRequest(BaseModel):
    patient_id: UUID
    features: dict  # Glucose, BMI, Age, etc.

class InferenceDLRequest(BaseModel):
    patient_id: UUID
    image_url: str  # URL de la imagen en MinIO