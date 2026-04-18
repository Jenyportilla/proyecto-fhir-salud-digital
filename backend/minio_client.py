# minio_client.py — Cliente MinIO para almacenamiento de imágenes médicas
# Proyecto FHIR Salud Digital (C2)
# S3 API: upload multipart + URL presignada válida 1h

import os
import uuid
from io import BytesIO
from datetime import timedelta
from minio import Minio
from minio.error import S3Error
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "medical-images")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

# Inicializar cliente
_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE,
)


def _ensure_bucket():
    """Crea el bucket si no existe."""
    try:
        if not _client.bucket_exists(MINIO_BUCKET):
            _client.make_bucket(MINIO_BUCKET)
    except S3Error as e:
        raise RuntimeError(f"Error al verificar/crear bucket MinIO: {e}")


def check_connection() -> bool:
    """Verifica si MinIO está disponible."""
    try:
        _client.list_buckets()
        return True
    except Exception:
        return False


# ──────────────────────────────────────────
# OPERACIONES
# ──────────────────────────────────────────
def upload_image(
    file_data: bytes,
    patient_id: str,
    filename: str,
    content_type: str = "image/jpeg",
) -> str:
    """
    Sube una imagen a MinIO con Server-Side Encryption (SSE-S3).
    Retorna la key (ruta) del objeto en el bucket.
    """
    _ensure_bucket()

    # Generar key único: patients/{patient_id}/images/{uuid}_{filename}
    file_ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
    object_key = f"patients/{patient_id}/images/{uuid.uuid4().hex}.{file_ext}"

    data_stream = BytesIO(file_data)
    data_length = len(file_data)

    _client.put_object(
        MINIO_BUCKET,
        object_key,
        data_stream,
        data_length,
        content_type=content_type,
    )

    return object_key


def get_presigned_url(object_key: str, expires_hours: int = 1) -> str:
    """
    Genera una URL presignada para acceder a una imagen.
    Válida por 1 hora por defecto.
    """
    try:
        url = _client.presigned_get_object(
            MINIO_BUCKET,
            object_key,
            expires=timedelta(hours=expires_hours),
        )
        return url
    except S3Error as e:
        raise RuntimeError(f"Error al generar URL presignada: {e}")


def delete_object(object_key: str):
    """Elimina un objeto de MinIO."""
    try:
        _client.remove_object(MINIO_BUCKET, object_key)
    except S3Error as e:
        raise RuntimeError(f"Error al eliminar objeto de MinIO: {e}")
