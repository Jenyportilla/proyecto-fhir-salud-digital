// pages/Login.jsx — Pantalla de login con doble API-Key
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Login.css';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [accessKey, setAccessKey] = useState('master-access-key');
  const [permissionKey, setPermissionKey] = useState('admin-permission');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showHabeas, setShowHabeas] = useState(false);

  const { login, acceptHabeasData } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    localStorage.setItem('accessKey', accessKey);
    localStorage.setItem('permissionKey', permissionKey);

    try {
      const userData = await login(email, password);
      if (!userData.habeas_data_accepted) {
        setShowHabeas(true);
      } else {
        navigate('/dashboard');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Error de conexion con el servidor');
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptHabeas = async () => {
    await acceptHabeasData();
    setShowHabeas(false);
    navigate('/dashboard');
  };

  return (
    <div className="login-page">
      <div className="login-bg-effects">
        <div className="bg-orb bg-orb-1" />
        <div className="bg-orb bg-orb-2" />
        <div className="bg-orb bg-orb-3" />
      </div>

      <div className="login-container animate-fade-in">
        <div className="login-header">
          <div className="login-logo-box">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>
            </svg>
          </div>
          <h1 className="login-title">FHIR Salud Digital</h1>
          <p className="login-subtitle">Sistema de Historia Clinica</p>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          {error && (
            <div className="login-error">
              <span>Error:</span> {error}
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Correo electronico</label>
            <input
              type="email"
              className="input"
              placeholder="usuario@clinica.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Contrasena</label>
            <input
              type="password"
              className="input"
              placeholder="********"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <details className="api-keys-section">
            <summary className="api-keys-toggle">API Keys (autenticacion doble)</summary>
            <div className="api-keys-fields">
              <div className="form-group">
                <label className="form-label">X-Access-Key</label>
                <input type="text" className="input" value={accessKey} onChange={(e) => setAccessKey(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">X-Permission-Key</label>
                <select className="input" value={permissionKey} onChange={(e) => setPermissionKey(e.target.value)}>
                  <option value="admin-permission">Admin</option>
                  <option value="medico-permission">Medico</option>
                  <option value="paciente-permission">Paciente</option>
                </select>
              </div>
            </div>
          </details>

          <button type="submit" className="btn btn-primary btn-lg login-btn" disabled={loading}>
            {loading ? <span className="spinner" /> : 'Iniciar Sesion'}
          </button>
        </form>

        <p className="login-footer-text">
          Protegido bajo Ley 1581/2012 | Datos cifrados AES-256
        </p>
      </div>

      {showHabeas && (
        <div className="modal-overlay">
          <div className="modal animate-fade-in">
            <div className="modal-header">
              <h2>Consentimiento de Habeas Data</h2>
            </div>
            <div className="modal-body">
              <p>
                De acuerdo con la <strong>Ley 1581 de 2012</strong> y el <strong>Decreto 1377 de 2013</strong>,
                autorizo el tratamiento de mis datos personales y datos sensibles de salud
                conforme a la politica de privacidad del sistema.
              </p>
              <ul className="habeas-list">
                <li>Sus datos seran utilizados exclusivamente para fines clinicos</li>
                <li>Los datos estan cifrados con AES-256</li>
                <li>Puede solicitar eliminacion en cualquier momento</li>
                <li>El acceso esta auditado y registrado</li>
              </ul>
            </div>
            <div className="modal-actions">
              <button className="btn btn-primary btn-lg" onClick={handleAcceptHabeas}>
                Acepto los terminos
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
