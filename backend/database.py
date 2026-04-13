# database.py — Conexión a PostgreSQL con SQLAlchemy
# Proyecto FHIR Salud Digital (C2)

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Si es URL de Render, corregir el prefix (Render usa postgres:// pero SQLAlchemy necesita postgresql://)
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Generador de sesiones de BD. Se usa como dependencia de FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()