# dl-service/app.py — Microservicio DL Imagen (Mock con Grad-CAM)
# Simula clasificación de retinopatía diabética + genera Grad-CAM heatmap

import io
import os
import random
import uuid
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageFilter, ImageDraw
import numpy as np

app = FastAPI(title="DL Service — Retinopathy Detection (ONNX Mock)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── MinIO config ───────────────────────────────────────────────
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "medical-images")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

SEVERITY_LABELS = {
    0: "No DR",
    1: "Mild",
    2: "Moderate",
    3: "Severe",
    4: "Proliferative DR",
}


def get_minio_client():
    from minio import Minio
    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
    )
    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET)
    return client


def generate_gradcam(image_bytes: bytes) -> bytes:
    """Genera un Grad-CAM mock: superpone un heatmap circular sobre la imagen."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    width, height = img.size

    # Crear heatmap circular en el centro
    heatmap = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(heatmap)

    # Centro aleatorio (cerca del centro de la imagen)
    cx = width // 2 + random.randint(-width // 6, width // 6)
    cy = height // 2 + random.randint(-height // 6, height // 6)
    max_radius = min(width, height) // 3

    # Dibujar círculos concéntricos con gradiente rojo → amarillo
    for r in range(max_radius, 0, -2):
        alpha = int(120 * (1 - r / max_radius))
        ratio = r / max_radius
        red = 255
        green = int(255 * ratio)
        blue = 0
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(red, green, blue, alpha),
        )

    # Aplicar blur para suavizar
    heatmap = heatmap.filter(ImageFilter.GaussianBlur(radius=15))

    # Superponer sobre imagen original
    result = img.copy()
    result.paste(heatmap, (0, 0), heatmap)

    # Guardar como bytes
    buf = io.BytesIO()
    result.save(buf, format="PNG", quality=90)
    buf.seek(0)
    return buf.read()


@app.post("/predict")
async def predict(
    patient_id: str = Form(...),
    file: UploadFile = File(...),
):
    image_bytes = await file.read()

    # Simular predicción
    severity = random.choices([0, 1, 2, 3, 4], weights=[30, 25, 20, 15, 10])[0]
    confidence = round(random.uniform(0.60, 0.98), 4)

    # Generar Grad-CAM
    gradcam_bytes = generate_gradcam(image_bytes)

    # Subir Grad-CAM a MinIO
    gradcam_key = f"gradcam/{patient_id}/{uuid.uuid4().hex[:8]}_gradcam.png"
    try:
        client = get_minio_client()
        client.put_object(
            MINIO_BUCKET,
            gradcam_key,
            io.BytesIO(gradcam_bytes),
            len(gradcam_bytes),
            content_type="image/png",
        )
        gradcam_url = f"http://{MINIO_ENDPOINT}/{MINIO_BUCKET}/{gradcam_key}"
    except Exception as e:
        gradcam_url = None
        print(f"Error uploading Grad-CAM: {e}")

    risk_score = severity / 4.0
    if risk_score >= 0.75:
        risk_category = "CRITICAL"
    elif risk_score >= 0.50:
        risk_category = "HIGH"
    elif risk_score >= 0.25:
        risk_category = "MEDIUM"
    else:
        risk_category = "LOW"

    return {
        "patient_id": patient_id,
        "model_type": "DL",
        "model_name": "aptos_retinopathy_int8_onnx_v1",
        "prediction": severity,
        "severity_label": SEVERITY_LABELS[severity],
        "confidence": confidence,
        "risk_score": round(risk_score, 4),
        "risk_category": risk_category,
        "risk_prediction": {
            label: round(random.uniform(0.01, 0.3) if i != severity else confidence, 4)
            for i, label in SEVERITY_LABELS.items()
        },
        "gradcam_url": gradcam_url,
        "gradcam_key": gradcam_key,
        "inference_time_ms": round(random.uniform(500, 2000), 1),
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "dl-service", "model": "aptos_retinopathy_int8_mock"}
