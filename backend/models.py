# models.py — Modelos SQLAlchemy para el proyecto FHIR Salud Digital (C2)
# Todas las tablas incluyen soft-delete (deleted_at) excepto audit_log

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Float, Boolean, Integer, Text, DateTime,
    ForeignKey, JSON, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────
# USUARIOS (Admin, Médico, Paciente)
# ──────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    identification_doc = Column(String(20), unique=True)
    role = Column(String(20), nullable=False)  # admin, medico, paciente
    is_active = Column(Boolean, default=True)
    habeas_data_accepted = Column(Boolean, default=False)
    habeas_data_timestamp = Column(DateTime(timezone=True))
    habeas_data_ip = Column(String(45))
    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'medico', 'paciente')", name="ck_user_role"),
    )

    # Relationships
    owned_patients = relationship("Patient", back_populates="owner", foreign_keys="Patient.owner_id")
    assigned_patients = relationship("Patient", back_populates="assigned_doctor", foreign_keys="Patient.assigned_doctor_id")
    signed_reports = relationship("RiskReport", back_populates="signer")
    audit_entries = relationship("AuditLog", back_populates="user")
    consents = relationship("Consent", back_populates="user")


# ──────────────────────────────────────────
# PACIENTES (FHIR Patient)
# ──────────────────────────────────────────
class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fhir_id = Column(String(255))  # ID en servidor HAPI FHIR
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    assigned_doctor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    name = Column(String(255), nullable=False)
    birth_date = Column(String(10))  # YYYY-MM-DD
    gender = Column(String(20))
    identification_doc = Column(Text)  # Encriptado
    medical_summary = Column(Text)     # Encriptado
    minio_key = Column(String(500))
    status = Column(String(20), default="active")
    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    owner = relationship("User", back_populates="owned_patients", foreign_keys=[owner_id])
    assigned_doctor = relationship("User", back_populates="assigned_patients", foreign_keys=[assigned_doctor_id])
    observations = relationship("Observation", back_populates="patient")
    risk_reports = relationship("RiskReport", back_populates="patient")
    images = relationship("Image", back_populates="patient")


# ──────────────────────────────────────────
# IMÁGENES MÉDICAS (FHIR Media → MinIO)
# ──────────────────────────────────────────
class Image(Base):
    __tablename__ = "images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    minio_key = Column(Text, nullable=False)          # Key del objeto en MinIO (cifrado)
    original_filename = Column(String(500))            # Nombre original del archivo
    content_type = Column(String(100), default="image/jpeg")
    modality = Column(String(50))                      # FUNDUS, XRAY, DERM, CT, MRI
    description = Column(Text)                         # Descripción clínica
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    deleted_at = Column(DateTime(timezone=True))       # Soft-delete
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    patient = relationship("Patient", back_populates="images")
    uploader = relationship("User")


# ──────────────────────────────────────────
# OBSERVACIONES (FHIR Observation) con LOINC
# ──────────────────────────────────────────
class Observation(Base):
    __tablename__ = "observations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    loinc_code = Column(String(20), nullable=False)  # Ej: 2339-0
    loinc_display = Column(String(255))                # Ej: "Glucose [Mass/volume]"
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)           # UCUM units
    effective_date = Column(DateTime(timezone=True), default=utcnow)
    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    patient = relationship("Patient", back_populates="observations")


# ──────────────────────────────────────────
# RISK REPORTS (FHIR RiskAssessment)
# ──────────────────────────────────────────
class RiskReport(Base):
    __tablename__ = "risk_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    model_type = Column(String(10), nullable=False)  # ML o DL
    risk_score = Column(Float)
    risk_category = Column(String(20))  # LOW, MEDIUM, HIGH, CRITICAL
    risk_prediction = Column(JSON)       # Probabilidades por clase
    shap_values = Column(JSON)           # Explicabilidad ML
    gradcam_url = Column(String(500))    # URL Grad-CAM en MinIO
    signed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    signed_at = Column(DateTime(timezone=True))  # NULL = pendiente
    clinical_notes = Column(Text)         # >= 30 chars
    feedback = Column(Text)
    fhir_resource = Column(JSON)          # RiskAssessment FHIR completo
    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        CheckConstraint("model_type IN ('ML', 'DL')", name="ck_report_model_type"),
    )

    # Relationships
    patient = relationship("Patient", back_populates="risk_reports")
    signer = relationship("User", back_populates="signed_reports")
    feedbacks = relationship("ModelFeedback", back_populates="risk_report")


# ──────────────────────────────────────────
# CONSENTIMIENTO (FHIR Consent / Habeas Data)
# ──────────────────────────────────────────
class Consent(Base):
    __tablename__ = "consent"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    consent_type = Column(String(50), nullable=False)  # habeas_data, fhir_consent
    version = Column(String(10), default="1.0")
    accepted = Column(Boolean, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utcnow)
    ip_address = Column(String(45))
    fhir_resource = Column(JSON)


    # Relationships
    user = relationship("User", back_populates="consents")


# ──────────────────────────────────────────
# COLA DE INFERENCIA (Orquestador)
# ──────────────────────────────────────────
class InferenceQueue(Base):
    __tablename__ = "inference_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    model_type = Column(String(10), nullable=False)  # ML, DL
    status = Column(String(20), default="PENDING")    # PENDING, RUNNING, DONE, ERROR
    result = Column(JSON)
    error_msg = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    patient = relationship("Patient")


# ──────────────────────────────────────────
# AUDIT LOG (INSERT-ONLY — jamás UPDATE/DELETE)
# ──────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    action = Column(String(50), nullable=False)     # LOGIN, LOGOUT, VIEW_PATIENT, etc.
    resource_type = Column(String(50))               # Patient, Observation, etc.
    resource_id = Column(String(255))
    status = Column(String(20), default="SUCCESS")
    details = Column(JSON)
    ip_address = Column(String(45))
    timestamp = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    user = relationship("User", back_populates="audit_entries")


# ──────────────────────────────────────────
# FEEDBACK DEL MODELO
# ──────────────────────────────────────────
class ModelFeedback(Base):
    __tablename__ = "model_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_report_id = Column(UUID(as_uuid=True), ForeignKey("risk_reports.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action = Column(String(20), nullable=False)  # ACCEPT, REJECT
    justification = Column(Text)                  # >= 20 chars si rechaza
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    risk_report = relationship("RiskReport", back_populates="feedbacks")
    doctor = relationship("User")