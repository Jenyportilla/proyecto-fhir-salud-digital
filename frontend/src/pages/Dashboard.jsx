// pages/Dashboard.jsx — Vista principal con metricas y resumen
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { patientsAPI, adminAPI } from '../services/api';
import './Dashboard.css';

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [recentPatients, setRecentPatients] = useState([]);
  const [totalPatients, setTotalPatients] = useState(0);
  const [pendingReports, setPendingReports] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const patientsRes = await patientsAPI.list(5, 0);
      setRecentPatients(patientsRes.data.data || []);
      setTotalPatients(patientsRes.data.total || 0);

      if (user?.role === 'admin') {
        const statsRes = await adminAPI.stats();
        setStats(statsRes.data);
      }

      if (user?.role === 'medico' || user?.role === 'admin') {
        try {
          const repRes = await patientsAPI.pendingReports();
          setPendingReports(repRes.data.data || []);
        } catch (e) {
          setPendingReports([]);
        }
      }
    } catch (err) {
      console.error('Error cargando dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  const goToPatient = (patientId) => {
    // Guardar ID para que Patients.jsx lo detecte
    sessionStorage.setItem('viewPatientId', patientId);
    navigate('/patients');
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner spinner-lg" />
        <p>Cargando dashboard...</p>
      </div>
    );
  }

  const getCategoryClass = (cat) => {
    if (cat === 'CRITICAL') return 'badge-danger';
    if (cat === 'HIGH') return 'badge-warning';
    if (cat === 'MEDIUM') return 'badge-info';
    return 'badge-success';
  };

  const greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return 'Buenos dias';
    if (h < 18) return 'Buenas tardes';
    return 'Buenas noches';
  };

  const roleLabel = { admin: 'Administrador', medico: 'Medico', paciente: 'Paciente' };

  return (
    <div className="dashboard animate-fade-in">
      {/* Welcome Banner */}
      <div className="welcome-banner">
        <div className="welcome-text">
          <p className="welcome-greeting">{greeting()},</p>
          <h1 className="welcome-name">{user?.full_name}</h1>
          <p className="welcome-role">{roleLabel[user?.role] || user?.role} | FHIR Salud Digital</p>
        </div>
        <div className="welcome-date">
          <span className="welcome-day">{new Date().toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}</span>
        </div>
      </div>

      {/* Stats Cards - visible para todos los roles */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon stat-icon-blue">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          </div>
          <div className="stat-info">
            <span className="stat-value">{stats?.users?.total || totalPatients}</span>
            <span className="stat-label">{user?.role === 'admin' ? 'Usuarios' : 'Mis Pacientes'}</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon stat-icon-green">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
          </div>
          <div className="stat-info">
            <span className="stat-value">{stats?.patients?.total || totalPatients}</span>
            <span className="stat-label">Pacientes Activos</span>
          </div>
        </div>

        {(user?.role === 'medico' || user?.role === 'admin') && (
          <div className="stat-card stat-card-warning">
            <div className="stat-icon stat-icon-orange">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
            </div>
            <div className="stat-info">
              <span className="stat-value">{pendingReports.length}</span>
              <span className="stat-label">Pendientes Firma</span>
            </div>
          </div>
        )}

        {stats && (
          <div className="stat-card">
            <div className="stat-icon stat-icon-purple">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
            </div>
            <div className="stat-info">
              <span className="stat-value">{stats.observations?.total || 0}</span>
              <span className="stat-label">Observaciones</span>
            </div>
          </div>
        )}
      </div>

      {/* Reportes pendientes de firma */}
      {(user?.role === 'medico' || user?.role === 'admin') && pendingReports.length > 0 && (
        <div className="card dashboard-section pending-section">
          <h3 className="section-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-warning)" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
            Reportes Pendientes de Firma
          </h3>
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Paciente</th>
                  <th>Modelo</th>
                  <th>Score</th>
                  <th>Categoria</th>
                  <th>Fecha</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {pendingReports.map((r) => (
                  <tr key={r.id}>
                    <td className="td-name">{r.patient_name}</td>
                    <td><span className={`badge ${r.model_type === 'ML' ? 'badge-info' : 'badge-warning'}`}>{r.model_type}</span></td>
                    <td className="td-name">{r.risk_score != null ? `${(r.risk_score * 100).toFixed(0)}%` : '\u2014'}</td>
                    <td><span className={`badge ${getCategoryClass(r.risk_category)}`}>{r.risk_category}</span></td>
                    <td className="td-date">{r.created_at?.split('T')[0] || '\u2014'}</td>
                    <td>
                      <button className="btn btn-primary btn-sm" onClick={() => goToPatient(r.patient_id)}>
                        Ver Paciente
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pacientes Recientes */}
      <div className="card dashboard-section">
        <h3 className="section-title">Pacientes Recientes</h3>
        {recentPatients.length > 0 ? (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Genero</th>
                  <th>Fecha Nac.</th>
                  <th>Estado</th>
                  <th>Creado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {recentPatients.map((p) => (
                  <tr key={p.id}>
                    <td className="td-name">{p.name}</td>
                    <td>{p.gender === 'male' ? 'Masculino' : p.gender === 'female' ? 'Femenino' : p.gender || '\u2014'}</td>
                    <td>{p.birth_date || '\u2014'}</td>
                    <td>
                      <span className={`badge ${p.status === 'active' ? 'badge-success' : 'badge-warning'}`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="td-date">{p.created_at?.split('T')[0] || '\u2014'}</td>
                    <td>
                      <button className="btn btn-secondary btn-sm" onClick={() => goToPatient(p.id)}>
                        Ver
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="empty-message">No hay pacientes disponibles</p>
        )}
      </div>
    </div>
  );
}
