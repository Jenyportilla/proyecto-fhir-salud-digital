// pages/Dashboard.jsx — Vista principal con metricas y resumen
import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { patientsAPI, adminAPI } from '../services/api';
import './Dashboard.css';

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [recentPatients, setRecentPatients] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const patientsRes = await patientsAPI.list(5, 0);
      setRecentPatients(patientsRes.data.data || []);
      if (user?.role === 'admin') {
        const statsRes = await adminAPI.stats();
        setStats(statsRes.data);
      }
    } catch (err) {
      console.error('Error cargando dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner spinner-lg" />
        <p>Cargando dashboard...</p>
      </div>
    );
  }

  return (
    <div className="dashboard animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Bienvenido, {user?.full_name}</p>
        </div>
        <span className={`badge ${user?.role === 'admin' ? 'badge-danger' : user?.role === 'medico' ? 'badge-info' : 'badge-success'}`}>
          {user?.role?.toUpperCase()}
        </span>
      </div>

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon stat-icon-blue">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            </div>
            <div className="stat-info">
              <span className="stat-value">{stats.users?.total || 0}</span>
              <span className="stat-label">Usuarios</span>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon stat-icon-green">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
            </div>
            <div className="stat-info">
              <span className="stat-value">{stats.patients?.total || 0}</span>
              <span className="stat-label">Pacientes</span>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon stat-icon-purple">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
            </div>
            <div className="stat-info">
              <span className="stat-value">{stats.observations?.total || 0}</span>
              <span className="stat-label">Observaciones</span>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon stat-icon-orange">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
            </div>
            <div className="stat-info">
              <span className="stat-value">{stats.risk_reports?.pending_signature || 0}</span>
              <span className="stat-label">Pendientes Firma</span>
            </div>
          </div>
        </div>
      )}

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
                </tr>
              </thead>
              <tbody>
                {recentPatients.map((p) => (
                  <tr key={p.id}>
                    <td className="td-name">{p.name}</td>
                    <td>{p.gender === 'male' ? 'Masculino' : p.gender === 'female' ? 'Femenino' : p.gender || '—'}</td>
                    <td>{p.birth_date || '—'}</td>
                    <td>
                      <span className={`badge ${p.status === 'active' ? 'badge-success' : 'badge-warning'}`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="td-date">{p.created_at?.split('T')[0] || '—'}</td>
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
