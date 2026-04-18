# ml-service/app.py — Microservicio ML Tabular (Mock con SHAP)
# Simula predicción de diabetes tipo PIMA con SHAP values

import random
import math
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="ML Service — Diabetes Risk (ONNX Mock)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Feature schema (PIMA Diabetes) ─────────────────────────────
class PredictRequest(BaseModel):
    patient_id: Optional[str] = None
    Pregnancies: float = 0
    Glucose: float = 100
    BloodPressure: float = 70
    SkinThickness: float = 20
    Insulin: float = 80
    BMI: float = 25.0
    DiabetesPedigreeFunction: float = 0.5
    Age: float = 30


# ── Rangos normales para calcular riesgo ───────────────────────
THRESHOLDS = {
    "Glucose": {"normal": 100, "high": 140, "weight": 0.30},
    "BMI": {"normal": 25, "high": 35, "weight": 0.20},
    "Age": {"normal": 30, "high": 55, "weight": 0.12},
    "BloodPressure": {"normal": 80, "high": 130, "weight": 0.10},
    "Insulin": {"normal": 80, "high": 200, "weight": 0.10},
    "DiabetesPedigreeFunction": {"normal": 0.3, "high": 1.0, "weight": 0.08},
    "SkinThickness": {"normal": 20, "high": 40, "weight": 0.05},
    "Pregnancies": {"normal": 2, "high": 8, "weight": 0.05},
}


def compute_risk(features: dict) -> dict:
    """Calcula riesgo simulado basado en los features."""
    score = 0.0
    shap_values = {}

    for feat, thres in THRESHOLDS.items():
        val = features.get(feat, thres["normal"])
        normal = thres["normal"]
        high = thres["high"]
        weight = thres["weight"]

        # Normalizar entre 0 y 1
        if high != normal:
            normalized = max(0, min(1, (val - normal) / (high - normal)))
        else:
            normalized = 0

        contribution = normalized * weight
        score += contribution

        # SHAP: contribución positiva si por encima de normal, negativa si por debajo
        shap_val = (val - normal) / max(1, (high - normal)) * weight
        shap_values[feat] = round(shap_val, 4)

    # Clamp score entre 0.05 y 0.98
    score = max(0.05, min(0.98, score))
    # Agregar ruido mínimo para realismo
    score += random.uniform(-0.03, 0.03)
    score = max(0.02, min(0.99, score))

    return {
        "probability": round(score, 4),
        "prediction": 1 if score >= 0.5 else 0,
        "shap_values": shap_values,
    }


@app.post("/predict")
def predict(req: PredictRequest):
    features = {
        "Pregnancies": req.Pregnancies,
        "Glucose": req.Glucose,
        "BloodPressure": req.BloodPressure,
        "SkinThickness": req.SkinThickness,
        "Insulin": req.Insulin,
        "BMI": req.BMI,
        "DiabetesPedigreeFunction": req.DiabetesPedigreeFunction,
        "Age": req.Age,
    }

    result = compute_risk(features)

    prob = result["probability"]
    if prob >= 0.75:
        risk_category = "CRITICAL"
    elif prob >= 0.50:
        risk_category = "HIGH"
    elif prob >= 0.30:
        risk_category = "MEDIUM"
    else:
        risk_category = "LOW"

    return {
        "patient_id": req.patient_id,
        "model_type": "ML",
        "model_name": "diabetes_pima_onnx_v1",
        "prediction": result["prediction"],
        "probability": prob,
        "risk_category": risk_category,
        "risk_prediction": {
            "diabetes_positive": prob,
            "diabetes_negative": round(1 - prob, 4),
        },
        "shap_values": result["shap_values"],
        "calibration": "isotonic",
        "inference_time_ms": round(random.uniform(50, 200), 1),
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "ml-service", "model": "diabetes_pima_onnx_mock"}
