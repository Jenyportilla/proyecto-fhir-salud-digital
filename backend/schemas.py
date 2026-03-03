# Define cómo deben verse los datos que entran y salen.

from pydantic import BaseModel
from datetime import date
from pydantic import BaseModel

class PatientCreate(BaseModel):
    name: str
    birthDate: date
    identification_doc: str

class ObservationCreate(BaseModel):
    patient_id: int
    type: str
    value: float
    unit: str