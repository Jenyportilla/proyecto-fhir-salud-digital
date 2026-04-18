# seed_db.py — Script para poblar la base de datos con datos de prueba
# Ejecutar: python seed_db.py

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

from database import SessionLocal, engine
from models import Base, User, Patient, Observation
from auth import hash_password

def seed():
    """Crea las tablas y pobla con datos de prueba."""

    # Crear todas las tablas
    print("Creando tablas en la base de datos...")
    Base.metadata.create_all(bind=engine)
    print("Tablas creadas correctamente")

    db = SessionLocal()

    try:
        # ── Verificar si ya hay usuarios ──
        existing_users = db.query(User).count()
        if existing_users > 0:
            print(f"Ya existen {existing_users} usuarios. Deseas reiniciar? (s/n)")
            resp = input().strip().lower()
            if resp != "s":
                print("Seed cancelado")
                return
            # Borrar todo en orden
            print("Limpiando datos existentes...")
            db.query(Observation).delete()
            db.query(Patient).delete()
            db.query(User).delete()
            db.commit()

        # ══════════════════════════════════════
        # USUARIOS
        # ══════════════════════════════════════
        print("\nCreando usuarios...")

        admin = User(
            email="admin@clinica.com",
            password_hash=hash_password("Admin2026!"),
            full_name="Administrador del Sistema",
            identification_doc="1000000001",
            role="admin",
            is_active=True,
            habeas_data_accepted=True,
            habeas_data_timestamp=datetime.now(timezone.utc),
        )

        medico1 = User(
            email="medico1@clinica.com",
            password_hash=hash_password("Medico2026!"),
            full_name="Dr. Carlos Ramírez",
            identification_doc="1000000005",
            role="medico",
            is_active=True,
            habeas_data_accepted=True,
            habeas_data_timestamp=datetime.now(timezone.utc),
        )

        medico2 = User(
            email="medico2@clinica.com",
            password_hash=hash_password("Medico2026!"),
            full_name="Dra. María López",
            identification_doc="1000000006",
            role="medico",
            is_active=True,
            habeas_data_accepted=True,
            habeas_data_timestamp=datetime.now(timezone.utc),
        )

        paciente_user = User(
            email="paciente@clinica.com",
            password_hash=hash_password("Paciente2026!"),
            full_name="Juan Pérez García",
            identification_doc="1000000007",
            role="paciente",
            is_active=True,
            habeas_data_accepted=False,  # Para testear el modal de Habeas Data
        )

        db.add_all([admin, medico1, medico2, paciente_user])
        db.flush()  # Para obtener los IDs

        print(f"   Admin:    {admin.email} (id: {admin.id})")
        print(f"   Médico 1: {medico1.email} (id: {medico1.id})")
        print(f"   Médico 2: {medico2.email} (id: {medico2.id})")
        print(f"   Paciente: {paciente_user.email} (id: {paciente_user.id})")

        # ══════════════════════════════════════
        # PACIENTES (30+ como requiere el proyecto)
        # ══════════════════════════════════════
        print("\nCreando pacientes de prueba...")

        pacientes_data = [
            {"name": "Ana María Gómez", "birth_date": "1985-03-15", "gender": "female", "identification_doc": "1012345678", "doctor": medico1},
            {"name": "Pedro Antonio Ruiz", "birth_date": "1978-07-22", "gender": "male", "identification_doc": "1023456789", "doctor": medico1},
            {"name": "Lucía Fernández Díaz", "birth_date": "1992-11-08", "gender": "female", "identification_doc": "1034567890", "doctor": medico1},
            {"name": "Carlos Eduardo Martínez", "birth_date": "1965-01-30", "gender": "male", "identification_doc": "1045678901", "doctor": medico1},
            {"name": "María José Torres", "birth_date": "2000-05-12", "gender": "female", "identification_doc": "1056789012", "doctor": medico1},
            {"name": "Andrés Felipe López", "birth_date": "1988-09-03", "gender": "male", "identification_doc": "1067890123", "doctor": medico1},
            {"name": "Valentina Restrepo", "birth_date": "1995-12-25", "gender": "female", "identification_doc": "1078901234", "doctor": medico2},
            {"name": "David Santiago Moreno", "birth_date": "1972-04-18", "gender": "male", "identification_doc": "1089012345", "doctor": medico2},
            {"name": "Camila Andrea Vargas", "birth_date": "1990-08-07", "gender": "female", "identification_doc": "1090123456", "doctor": medico2},
            {"name": "Santiago Herrera Castillo", "birth_date": "1983-02-14", "gender": "male", "identification_doc": "1101234567", "doctor": medico2},
            {"name": "Daniela Alejandra Ríos", "birth_date": "1998-06-30", "gender": "female", "identification_doc": "1112345678", "doctor": medico2},
            {"name": "Juan David Ospina", "birth_date": "1970-10-11", "gender": "male", "identification_doc": "1123456789", "doctor": medico2},
            {"name": "Isabella Muñoz Peña", "birth_date": "2002-01-20", "gender": "female", "identification_doc": "1134567890", "doctor": medico1},
            {"name": "Miguel Ángel Cardona", "birth_date": "1960-11-05", "gender": "male", "identification_doc": "1145678901", "doctor": medico1},
            {"name": "Sara Valentina Gil", "birth_date": "1993-07-16", "gender": "female", "identification_doc": "1156789012", "doctor": medico1},
            {"name": "Sebastián Duque", "birth_date": "1987-03-28", "gender": "male", "identification_doc": "1167890123", "doctor": medico2},
            {"name": "Laura Patricia Mejía", "birth_date": "1975-09-09", "gender": "female", "identification_doc": "1178901234", "doctor": medico2},
            {"name": "Alejandro Botero Arias", "birth_date": "1999-04-22", "gender": "male", "identification_doc": "1189012345", "doctor": medico1},
            {"name": "Natalia Correa Salazar", "birth_date": "1982-12-01", "gender": "female", "identification_doc": "1190123456", "doctor": medico2},
            {"name": "Diego Hernán Rojas", "birth_date": "1968-06-14", "gender": "male", "identification_doc": "1201234567", "doctor": medico1},
            {"name": "Paula Andrea Castaño", "birth_date": "1996-02-28", "gender": "female", "identification_doc": "1212345678", "doctor": medico1},
            {"name": "Fernando José Arango", "birth_date": "1973-08-17", "gender": "male", "identification_doc": "1223456789", "doctor": medico2},
            {"name": "Mariana Soto Velásquez", "birth_date": "2001-10-03", "gender": "female", "identification_doc": "1234567890", "doctor": medico2},
            {"name": "Ricardo Esteban Zuluaga", "birth_date": "1986-05-21", "gender": "male", "identification_doc": "1245678901", "doctor": medico1},
            {"name": "Juliana Posada Henao", "birth_date": "1991-01-07", "gender": "female", "identification_doc": "1256789012", "doctor": medico1},
            {"name": "Gustavo Adolfo Parra", "birth_date": "1963-11-19", "gender": "male", "identification_doc": "1267890123", "doctor": medico2},
            {"name": "Carolina Alzate Ossa", "birth_date": "1997-07-24", "gender": "female", "identification_doc": "1278901234", "doctor": medico2},
            {"name": "Héctor Fabio Gallego", "birth_date": "1980-03-10", "gender": "male", "identification_doc": "1289012345", "doctor": medico1},
            {"name": "Andrea Milena Cano", "birth_date": "1994-09-15", "gender": "female", "identification_doc": "1290123456", "doctor": medico2},
            {"name": "Óscar Iván Quintero", "birth_date": "1976-12-08", "gender": "male", "identification_doc": "1301234567", "doctor": medico1},
            {"name": "Juan Pérez García", "birth_date": "1990-06-20", "gender": "male", "identification_doc": "1312345678", "doctor": medico1},
        ]

        patients = []
        for i, p_data in enumerate(pacientes_data):
            patient = Patient(
                name=p_data["name"],
                birth_date=p_data["birth_date"],
                gender=p_data["gender"],
                identification_doc=p_data["identification_doc"],
                assigned_doctor_id=p_data["doctor"].id,
                owner_id=paciente_user.id if i == len(pacientes_data) - 1 else None,
                status="active",
            )
            patients.append(patient)

        db.add_all(patients)
        db.flush()
        print(f"   {len(patients)} pacientes creados")

        # ══════════════════════════════════════
        # OBSERVACIONES DE PRUEBA (con códigos LOINC)
        # ══════════════════════════════════════
        print("\nCreando observaciones de prueba...")

        loinc_codes = [
            {"code": "2339-0",  "display": "Glucosa",            "unit": "mg/dL",  "min": 70,  "max": 200},
            {"code": "55284-4", "display": "Presión Arterial",   "unit": "mmHg",   "min": 90,  "max": 180},
            {"code": "39156-5", "display": "BMI",                "unit": "kg/m2",  "min": 18,  "max": 40},
            {"code": "14749-6", "display": "Insulina",           "unit": "µU/mL",  "min": 2,   "max": 30},
            {"code": "8310-5",  "display": "Temperatura",        "unit": "°C",     "min": 35,  "max": 40},
            {"code": "8867-4",  "display": "Frecuencia Cardíaca","unit": "lpm",    "min": 50,  "max": 120},
        ]

        import random
        random.seed(42)
        obs_count = 0

        for patient in patients:  # Observaciones para TODOS los pacientes
            for loinc in loinc_codes:
                for _ in range(3):  # 3 observaciones por tipo
                    obs = Observation(
                        patient_id=patient.id,
                        loinc_code=loinc["code"],
                        loinc_display=loinc["display"],
                        value=round(random.uniform(loinc["min"], loinc["max"]), 1),
                        unit=loinc["unit"],
                    )
                    db.add(obs)
                    obs_count += 1

        print(f"   {obs_count} observaciones creadas")

        # ══════════════════════════════════════
        # RISK REPORTS DE PRUEBA
        # ══════════════════════════════════════
        print("\nCreando risk reports de prueba...")

        from models import RiskReport
        reports_count = 0

        # Crear reports para los primeros 10 pacientes (mix firmados/pendientes)
        for i, patient in enumerate(patients[:10]):
            risk_score = round(random.uniform(0.1, 0.95), 4)
            if risk_score >= 0.75:
                category = "CRITICAL"
            elif risk_score >= 0.50:
                category = "HIGH"
            elif risk_score >= 0.30:
                category = "MEDIUM"
            else:
                category = "LOW"

            report = RiskReport(
                patient_id=patient.id,
                model_type=random.choice(["ML", "DL"]),
                risk_score=risk_score,
                risk_category=category,
                risk_prediction={
                    "diabetes_positive": risk_score,
                    "diabetes_negative": round(1 - risk_score, 4),
                },
                shap_values={
                    "Glucose": round(random.uniform(-0.1, 0.3), 4),
                    "BMI": round(random.uniform(-0.05, 0.2), 4),
                    "Age": round(random.uniform(-0.05, 0.12), 4),
                    "BloodPressure": round(random.uniform(-0.05, 0.1), 4),
                    "Insulin": round(random.uniform(-0.05, 0.1), 4),
                },
            )

            # Firmar la mitad de los reports
            if i < 5:
                report.signed_by = medico1.id if patient.assigned_doctor_id == medico1.id else medico2.id
                report.signed_at = datetime.now(timezone.utc)
                report.clinical_notes = f"Paciente evaluado. Score {category}. Se recomienda seguimiento."
                report.feedback = "ACCEPT"

            db.add(report)
            reports_count += 1

        print(f"   {reports_count} risk reports creados ({reports_count // 2} firmados, {reports_count - reports_count // 2} pendientes)")

        # ── Commit todo ──
        db.commit()

        print("\n" + "=" * 50)
        print(" SEED COMPLETADO EXITOSAMENTE")
        print("=" * 50)
        print("\nCredenciales de prueba:")
        print("┌──────────────┬──────────────────────┬────────────────┐")
        print("│ Rol          │ Email                │ Contraseña     │")
        print("├──────────────┼──────────────────────┼────────────────┤")
        print("│ Admin        │ admin@clinica.com    │ Admin2026!     │")
        print("│ Médico 1     │ medico1@clinica.com  │ Medico2026!    │")
        print("│ Médico 2     │ medico2@clinica.com  │ Medico2026!    │")
        print("│ Paciente     │ paciente@clinica.com │ Paciente2026!  │")
        print("└──────────────┴──────────────────────┴────────────────┘")
        print(f"\n Resumen: {4} usuarios, {len(patients)} pacientes, {obs_count} observaciones, {reports_count} risk reports")
        print("\n API Keys para headers:")
        print("  X-Access-Key: master-access-key")
        print("  X-Permission-Key: admin-permission | medico-permission | paciente-permission")

    except Exception as e:
        db.rollback()
        print(f"\n Error durante el seed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
