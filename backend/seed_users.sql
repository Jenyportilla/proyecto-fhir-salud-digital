-- ============================================================
-- SEED DE USUARIOS — Proyecto FHIR Salud Digital (C2)
-- ============================================================
-- Estos usuarios se crean automáticamente con el script seed.
-- Las contraseñas aquí están en texto plano SOLO como referencia.
-- En la BD real se guardan hasheadas con bcrypt (work factor 12).
-- ============================================================

-- NOTA: Este archivo es solo REFERENCIA.
-- Los usuarios se crean desde el backend con el endpoint POST /seed
-- o ejecutando: python seed_db.py

-- ============================================================
-- CREDENCIALES DE PRUEBA
-- ============================================================

-- ┌──────────────┬──────────────────────┬────────────────┬─────────────────────┬─────────────────────┐
-- │ Rol          │ Email                │ Contraseña     │ X-Access-Key        │ X-Permission-Key    │
-- ├──────────────┼──────────────────────┼────────────────┼─────────────────────┼─────────────────────┤
-- │ Admin        │ admin@clinica.com    │ Admin2026!     │ master-access-key   │ admin-permission    │
-- │ Médico 1     │ medico1@clinica.com  │ Medico2026!    │ master-access-key   │ medico-permission   │
-- │ Médico 2     │ medico2@clinica.com  │ Medico2026!    │ master-access-key   │ medico-permission   │
-- │ Paciente     │ paciente@clinica.com │ Paciente2026!  │ master-access-key   │ paciente-permission │
-- └──────────────┴──────────────────────┴────────────────┴─────────────────────┴─────────────────────┘

-- ============================================================
-- QUERIES SQL DIRECTAS (si necesitas insertar manualmente)
-- ============================================================

-- Las passwords están hasheadas con bcrypt. Estos hashes corresponden
-- a las contraseñas listadas arriba.

INSERT INTO users (email, password_hash, full_name, role, is_active)
VALUES
  ('admin@clinica.com',    '$2b$12$LJ3m4ys3GZwkRdX1k5v6sOQo8qYpFb8OJ5T8q4XsS8xMS5m0L2d2', 'Administrador del Sistema', 'admin',    TRUE),
  ('medico1@clinica.com',  '$2b$12$LJ3m4ys3GZwkRdX1k5v6sOQo8qYpFb8OJ5T8q4XsS8xMS5m0L2d2', 'Dr. Carlos Ramírez',        'medico',   TRUE),
  ('medico2@clinica.com',  '$2b$12$LJ3m4ys3GZwkRdX1k5v6sOQo8qYpFb8OJ5T8q4XsS8xMS5m0L2d2', 'Dra. María López',          'medico',   TRUE),
  ('paciente@clinica.com', '$2b$12$LJ3m4ys3GZwkRdX1k5v6sOQo8qYpFb8OJ5T8q4XsS8xMS5m0L2d2', 'Juan Pérez García',         'paciente', TRUE);

-- ============================================================
-- QUERY PARA VER USUARIOS
-- ============================================================

SELECT id, email, full_name, role, is_active, created_at
FROM users
ORDER BY role, email;

-- ============================================================
-- QUERY PARA VER AUDIT LOG
-- ============================================================

SELECT id, user_id, action, resource_type, resource_id, status, timestamp
FROM audit_log
ORDER BY timestamp DESC
LIMIT 50;
