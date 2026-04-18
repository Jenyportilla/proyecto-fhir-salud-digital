# routers/images.py — Gestión de imágenes médicas (FHIR Media → MinIO)
# Upload multipart + URL presignada válida 1h
# Audit log: UPLOAD_IMAGE en cada subida

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from uuid import UUID

from database import get_db
from models import User, Patient, Image
from schemas import ImageResponse
from auth import get_current_user, require_medico_or_admin, log_audit
from encryption import encrypt_field, decrypt_field

router = APIRouter(prefix="/fhir/Media", tags=["Imagenes Medicas (FHIR Media)"])

# Tamaño máximo: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/dicom",
    "image/tiff", "application/dicom",
}
ALLOWED_MODALITIES = {"FUNDUS", "XRAY", "DERM", "CT", "MRI", "US", "OTHER"}


@router.post("", status_code=201)
async def upload_image(
    patient_id: str = Form(...),
    modality: str = Form("OTHER"),
    description: str = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(require_medico_or_admin),
    db: Session = Depends(get_db),
):
    """
    Subir imagen médica a MinIO.
    - Solo médicos y admins pueden subir.
    - El archivo se almacena en MinIO y se registra en la tabla images.
    - La key de MinIO se cifra con AES-256 en la BD.
    """
    # Validar modalidad
    if modality.upper() not in ALLOWED_MODALITIES:
        raise HTTPException(
            status_code=400,
            detail=f"Modalidad inválida. Opciones: {', '.join(ALLOWED_MODALITIES)}",
        )

    # Validar que el paciente existe
    patient = db.query(Patient).filter(
        Patient.id == UUID(patient_id),
        Patient.deleted_at.is_(None),
    ).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # Leer archivo
    file_data = await file.read()

    # Validar tamaño
    if len(file_data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Archivo demasiado grande (máx 10MB)")

    # Validar tipo de contenido
    content_type = file.content_type or "image/jpeg"
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido: {content_type}",
        )

    # Subir a MinIO
    try:
        from minio_client import upload_image as minio_upload, check_connection

        if not check_connection():
            raise HTTPException(
                status_code=503,
                detail="MinIO no disponible. Verifique que el servicio esté corriendo.",
            )

        object_key = minio_upload(
            file_data=file_data,
            patient_id=patient_id,
            filename=file.filename,
            content_type=content_type,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir imagen: {str(e)}")

    # Guardar registro en BD con key cifrada
    image_record = Image(
        patient_id=UUID(patient_id),
        minio_key=encrypt_field(object_key),
        original_filename=file.filename,
        content_type=content_type,
        modality=modality.upper(),
        description=description,
        uploaded_by=current_user.id,
    )
    db.add(image_record)
    db.commit()
    db.refresh(image_record)

    # Audit log
    log_audit(
        db, current_user.id, "UPLOAD_IMAGE", "Image",
        str(image_record.id),
        details={"patient_id": patient_id, "modality": modality, "filename": file.filename},
    )

    return {
        "message": "Imagen subida exitosamente",
        "id": str(image_record.id),
        "patient_id": patient_id,
        "modality": modality.upper(),
    }


@router.get("/patient/{patient_id}")
def list_patient_images(
    patient_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Listar imágenes de un paciente.
    Retorna URLs presignadas válidas por 1 hora.
    """
    # Verificar que el paciente existe
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

    images = db.query(Image).filter(
        Image.patient_id == patient_id,
        Image.deleted_at.is_(None),
    ).order_by(Image.created_at.desc()).all()

    # Generar URLs presignadas
    result = []
    for img in images:
        presigned_url = None
        try:
            from minio_client import get_presigned_url, check_connection
            if check_connection():
                decrypted_key = decrypt_field(img.minio_key)
                presigned_url = get_presigned_url(decrypted_key)
        except Exception:
            presigned_url = None

        result.append({
            "id": str(img.id),
            "patient_id": str(img.patient_id),
            "original_filename": img.original_filename,
            "content_type": img.content_type,
            "modality": img.modality,
            "description": img.description,
            "uploaded_by": str(img.uploaded_by) if img.uploaded_by else None,
            "presigned_url": presigned_url,
            "created_at": img.created_at.isoformat() if img.created_at else None,
        })

    return {"total": len(result), "data": result}


@router.get("/{image_id}")
def get_image(
    image_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtener detalle de una imagen con URL presignada."""
    image = db.query(Image).filter(
        Image.id == image_id,
        Image.deleted_at.is_(None),
    ).first()

    if not image:
        raise HTTPException(status_code=404, detail="Imagen no encontrada")

    # RBAC via paciente
    patient = db.query(Patient).filter(Patient.id == image.patient_id).first()
    if current_user.role == "paciente" and patient.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta imagen")
    if current_user.role == "medico" and patient.assigned_doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Esta imagen no pertenece a un paciente tuyo")

    # URL presignada
    presigned_url = None
    try:
        from minio_client import get_presigned_url, check_connection
        if check_connection():
            decrypted_key = decrypt_field(image.minio_key)
            presigned_url = get_presigned_url(decrypted_key)
    except Exception:
        presigned_url = None

    return {
        "id": str(image.id),
        "patient_id": str(image.patient_id),
        "original_filename": image.original_filename,
        "content_type": image.content_type,
        "modality": image.modality,
        "description": image.description,
        "uploaded_by": str(image.uploaded_by) if image.uploaded_by else None,
        "presigned_url": presigned_url,
        "created_at": image.created_at.isoformat() if image.created_at else None,
    }


@router.delete("/{image_id}")
def delete_image(
    image_id: UUID,
    current_user: User = Depends(require_medico_or_admin),
    db: Session = Depends(get_db),
):
    """Soft-delete de imagen médica."""
    image = db.query(Image).filter(
        Image.id == image_id,
        Image.deleted_at.is_(None),
    ).first()

    if not image:
        raise HTTPException(status_code=404, detail="Imagen no encontrada")

    image.deleted_at = datetime.now(timezone.utc)
    db.commit()

    log_audit(
        db, current_user.id, "DELETE_IMAGE", "Image",
        str(image_id),
        details={"patient_id": str(image.patient_id)},
    )

    return {"message": "Imagen eliminada (soft-delete)", "id": str(image_id)}
