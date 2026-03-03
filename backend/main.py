from fastapi import FastAPI, Header, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from database import engine, SessionLocal
from models import Base, Patient, Observation
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from slowapi import Limiter
from slowapi.util import get_remote_address
from schemas import PatientCreate, ObservationCreate
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
import os

# Cargar variables de entorno PRIMERO
load_dotenv()

# Crear app PRIMERO
app = FastAPI()

# Configurar CORS (para que Swagger UI y Streamlit funcionen)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear tablas en la base de datos
Base.metadata.create_all(bind=engine)

# Rate limiter (Anti-DoS) - Requerimiento D.2
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Encriptación (Criptografía para datos sensibles) - Requerimiento D.1
fernet = Fernet(os.getenv("FERNET_KEY"))

def encrypt_data(data):
    return fernet.encrypt(data.encode()).decode()

def decrypt_data(data):
    try:
        return fernet.decrypt(data.encode()).decode()
    except:
        return data  # Si falla, devolver original

# Validación de API Keys (Doble autenticación) - Requerimiento B.2
def validate_keys(
    x_access_key: str = Header(...),
    x_permission_key: str = Header(...)
):
    if x_access_key != os.getenv("ACCESS_KEY"):
        raise HTTPException(status_code=401, detail="❌ Invalid access key")
    
    # Validar que la permission key exista
    valid_keys = [
        os.getenv("ADMIN_KEY"),
        os.getenv("DOCTOR_KEY"),
        os.getenv("PATIENT_KEY")
    ]
    
    if x_permission_key not in valid_keys:
        raise HTTPException(status_code=403, detail="❌ Invalid permission key")
    
    return x_permission_key


# ============================================================================
# ENDPOINTS DE PACIENTES
# ============================================================================

# Endpoint raíz
@app.get("/")
def root():
    return {"message": "Servidor FHIR funcionando"}


# Endpoint GET paginado para Pacientes - Requerimiento C.2
@app.get("/fhir/Patient")
def get_patients(limit: int = 10, offset: int = 0, role=Depends(validate_keys)):
    db = SessionLocal()
    patients = db.query(Patient).offset(offset).limit(limit).all()
    db.close()  # Cerrar conexión a la BD
    return patients


# Endpoint POST para Pacientes (con Rate-Limiting) - Requerimiento D.2
@app.post("/fhir/Patient")
@limiter.limit("5/minute")
def create_patient(
    request: Request,
    patient_data: PatientCreate,
    role=Depends(validate_keys)
):
    db = SessionLocal()

    # Encriptar documento (Requerimiento D.1)
    encrypted_doc = encrypt_data(patient_data.identification_doc)

    new_patient = Patient(
        name=patient_data.name,
        birth_date=patient_data.birthDate,
        identification_doc=encrypted_doc
    )

    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    db.close()  # Cerrar conexión

    return {
        "message": "Paciente creado correctamente",
        "id": new_patient.id
    }


# Endpoint DELETE para Pacientes (Solo ADMIN) - Requerimiento B.1
@app.delete("/fhir/Patient/{patient_id}")
def delete_patient(patient_id: int, role=Depends(validate_keys)):
    # Verificar que solo ADMIN pueda borrar
    if role != os.getenv("ADMIN_KEY"):
        raise HTTPException(status_code=403, detail="🚫 Solo ADMIN puede eliminar pacientes")
    
    db = SessionLocal()
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    
    if not patient:
        db.close()
        raise HTTPException(status_code=404, detail="🚫 Paciente no encontrado")
    
    db.delete(patient)
    db.commit()
    db.close()
    
    return {"message": "Paciente eliminado correctamente", "id": patient_id}


# ============================================================================
# ENDPOINTS DE OBSERVACIONES (Signos Vitales)
# ============================================================================

# Endpoint GET para Observaciones (con nombre del paciente) - Requerimiento C.1
@app.get("/fhir/Observation")
def get_observations(role=Depends(validate_keys)):
    db = SessionLocal()
    
    # Consulta con JOIN para traer el nombre del paciente
    observaciones = db.query(
        Observation.id,
        Observation.patient_id,
        Observation.type,
        Observation.value,
        Observation.unit,
        Patient.name.label("patient_name")  # Nombre del paciente
    ).join(Patient, Observation.patient_id == Patient.id).all()
    
    db.close()
    
    # Convertir a lista de diccionarios para JSON
    result = []
    for obs in observaciones:
        result.append({
            "id": obs.id,
            "patient_id": obs.patient_id,
            "patient_name": obs.patient_name,  # Nombre del paciente
            "type": obs.type,
            "value": obs.value,
            "unit": obs.unit
        })
    
    return result


# Endpoint POST para Observaciones (con Rate-Limiting) - Requerimiento D.2
@app.post("/fhir/Observation")
@limiter.limit("10/minute")
def create_observation(
    request: Request,
    observation_data: ObservationCreate,
    role=Depends(validate_keys)
):
    db = SessionLocal()

    # Verificar que el paciente exista (Foreign Key) - Requerimiento A.2
    patient = db.query(Patient).filter(Patient.id == observation_data.patient_id).first()

    if not patient:
        db.close()
        raise HTTPException(status_code=404, detail="🚫 Paciente no encontrado")

    new_observation = Observation(
        patient_id=observation_data.patient_id,
        type=observation_data.type,
        value=observation_data.value,
        unit=observation_data.unit
    )

    db.add(new_observation)
    db.commit()
    db.refresh(new_observation)
    db.close()  # Cerrar conexión

    return {
        "message": "Observación creada correctamente",
        "id": new_observation.id
    }


# ============================================================================
# ENDPOINT DELETE PARA OBSERVACIONES (Solo ADMIN)
# ============================================================================

@app.delete("/fhir/Observation/{observation_id}")
def delete_observation(observation_id: int, role=Depends(validate_keys)):
    # Verificar que solo ADMIN pueda borrar
    if role != os.getenv("ADMIN_KEY"):
        raise HTTPException(status_code=403, detail="🚫 Solo ADMIN puede eliminar observaciones")
    
    db = SessionLocal()
    observation = db.query(Observation).filter(Observation.id == observation_id).first()
    
    if not observation:
        db.close()
        raise HTTPException(status_code=404, detail="🚫 Observación no encontrada")
    
    db.delete(observation)
    db.commit()
    db.close()
    
    return {"message": "Observación eliminada correctamente", "id": observation_id}