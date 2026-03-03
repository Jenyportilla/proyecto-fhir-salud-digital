# Define cómo se ven los datos en la base de datos.

from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Patient(Base):
    __tablename__ = "patient"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    birth_date = Column(String)
    identification_doc = Column(String)

    observations = relationship("Observation", back_populates="patient")

class Observation(Base):
    __tablename__ = "observation"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patient.id"))
    type = Column(String)
    value = Column(Float)
    unit = Column(String)

    patient = relationship("Patient", back_populates="observations")