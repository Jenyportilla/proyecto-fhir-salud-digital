# encryption.py — Cifrado AES-256 (Fernet) para campos sensibles
# Proyecto FHIR Salud Digital (C2)
# Cumple requisito: pgcrypto.encrypt(value, key, 'aes') a nivel aplicación

import os
import base64
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────
# CONFIGURACIÓN DE CLAVE
# ──────────────────────────────────────────
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    raise RuntimeError(
        "ENCRYPTION_KEY no configurada en .env. "
        "Genera una con: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    )

_fernet = Fernet(ENCRYPTION_KEY.encode())


# ──────────────────────────────────────────
# FUNCIONES DE CIFRADO / DESCIFRADO
# ──────────────────────────────────────────
def encrypt_field(value: str) -> str:
    """
    Cifra un valor de texto con AES-256 (Fernet).
    Retorna el texto cifrado en base64.
    Si el valor es None o vacío, retorna tal cual.
    """
    if not value:
        return value
    encrypted = _fernet.encrypt(value.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_field(value: str) -> str:
    """
    Descifra un valor cifrado con Fernet.
    Si el valor no parece estar cifrado (no empieza con 'gAAAAA'),
    lo retorna sin descifrar (compatibilidad con datos legacy).
    """
    if not value:
        return value
    # Detectar si el valor está cifrado (tokens Fernet empiezan con 'gAAAAA')
    if not value.startswith("gAAAAA"):
        return value  # Dato legacy sin cifrar
    try:
        decrypted = _fernet.decrypt(value.encode("utf-8"))
        return decrypted.decode("utf-8")
    except Exception:
        # Si falla el descifrado, retornar el valor original
        return value
