# main.py — Aplicación FastAPI principal
# Proyecto FHIR Salud Digital (C2)

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

from database import engine
from models import Base

# Cargar variables de entorno
load_dotenv()

# ──────────────────────────────────────────
# CREAR APP
# ──────────────────────────────────────────
app = FastAPI(
    title="API FHIR - Salud Digital",
    description="Sistema de gestión de historias clínicas basado en HL7 FHIR R4",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ──────────────────────────────────────────
# MIDDLEWARE
# ──────────────────────────────────────────

# CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiter (Anti-DoS)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Demasiadas solicitudes. Intenta de nuevo más tarde."},
    )

# ──────────────────────────────────────────
# CREAR TABLAS
# ──────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ──────────────────────────────────────────
# REGISTRAR ROUTERS
# ──────────────────────────────────────────
from routers.auth_router import router as auth_router
from routers.patients import router as patients_router
from routers.observations import router as observations_router
from routers.admin import router as admin_router
from routers.images import router as images_router
from routers.inference import router as inference_router

app.include_router(auth_router)
app.include_router(patients_router)
app.include_router(observations_router)
app.include_router(admin_router)
app.include_router(images_router)
app.include_router(inference_router)


# ──────────────────────────────────────────
# ENDPOINTS RAÍZ
# ──────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {
        "message": "API FHIR Salud Digital - Funcionando",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}