// pages/PatientDetail.jsx — Ficha clinica con observaciones y graficas
import { useState, useEffect } from 'react';
import { observationsAPI } from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import './PatientDetail.css';

export default function PatientDetail({ patientId, onBack }) {
  const [patient, setPatient] = useState(null);
  const [observations, setObservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortField, setSortField] = useState('effective_date');
  const [sortDir, setSortDir] = useState('desc');

  useEffect(() => { loadData(); }, [patientId]);

  const loadData = async () => {
    try {
      const [patRes, obsRes] = await Promise.all([
        import('../services/api').then((m) => m.patientsAPI.get(patientId)),
        observationsAPI.list(patientId, 100, 0),
      ]);
      setPatient(patRes.data);
      setObservations(obsRes.data.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSort = (field) => {
    if (sortField === field) setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDir('asc'); }
  };

  const SortIcon = ({ field }) => (
    <span className="sort-icon">
      {sortField === field ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ' ⇅'}
    </span>
  );

  if (loading) {
    return <div className="loading-container"><div className="spinner spinner-lg" /></div>;
  }

  const obsTypes = {};
  observations.forEach((o) => {
    const key = o.loinc_display || o.loinc_code;
    if (!obsTypes[key]) obsTypes[key] = [];
    obsTypes[key].push({
      date: o.effective_date?.split('T')[0] || '',
      value: o.value,
      unit: o.unit,
    });
  });

  const sortedObs = [...observations].sort((a, b) => {
    let aVal = a[sortField] ?? '';
    let bVal = b[sortField] ?? '';
    if (sortField === 'value') { aVal = Number(aVal); bVal = Number(bVal); return sortDir === 'asc' ? aVal - bVal : bVal - aVal; }
    const cmp = String(aVal).localeCompare(String(bVal));
    return sortDir === 'asc' ? cmp : -cmp;
  });

  const CHART_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

  return (
    <div className="patient-detail animate-fade-in">
      <button className="btn btn-secondary btn-sm" onClick={onBack}>
        ← Volver a pacientes
      </button>

      <div className="patient-header card">
        <div className="patient-avatar-lg">
          {patient?.name?.charAt(0).toUpperCase()}
        </div>
        <div className="patient-info-grid">
          <div>
            <h2 className="patient-name-lg">{patient?.name}</h2>
            <span className={`badge ${patient?.status === 'active' ? 'badge-success' : 'badge-warning'}`}>
              {patient?.status}
            </span>
          </div>
          <div className="patient-meta">
            <div className="meta-item">
              <span className="meta-label">Genero</span>
              <span className="meta-value">{patient?.gender === 'male' ? 'Masculino' : 'Femenino'}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Fecha de nacimiento</span>
              <span className="meta-value">{patient?.birth_date || '—'}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Documento</span>
              <span className="meta-value mono">{patient?.identification_doc || '—'}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Creado</span>
              <span className="meta-value">{patient?.created_at?.split('T')[0] || '—'}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Actualizado</span>
              <span className="meta-value">{patient?.updated_at?.split('T')[0] || '—'}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3 className="section-title">Tendencias de Signos Vitales</h3>
        {Object.keys(obsTypes).length > 0 ? (
          <div className="charts-grid">
            {Object.entries(obsTypes).map(([type, data], i) => (
              <div key={type} className="chart-container">
                <h4 className="chart-title">
                  {type} <span className="chart-unit">({data[0]?.unit})</span>
                </h4>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis dataKey="date" stroke="var(--color-text-muted)" fontSize={11} />
                    <YAxis stroke="var(--color-text-muted)" fontSize={11} />
                    <Tooltip
                      contentStyle={{
                        background: 'var(--color-bg-card)',
                        border: '1px solid var(--color-border)',
                        borderRadius: '8px',
                        color: 'var(--color-text-primary)',
                      }}
                    />
                    <Line type="monotone" dataKey="value" stroke={CHART_COLORS[i % CHART_COLORS.length]} strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ))}
          </div>
        ) : (
          <p className="empty-message">No hay observaciones para este paciente</p>
        )}
      </div>

      <div className="card">
        <h3 className="section-title">Historial de Observaciones</h3>
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th className="sortable" onClick={() => handleSort('loinc_code')}>Codigo LOINC<SortIcon field="loinc_code" /></th>
                <th className="sortable" onClick={() => handleSort('loinc_display')}>Tipo<SortIcon field="loinc_display" /></th>
                <th className="sortable" onClick={() => handleSort('value')}>Valor<SortIcon field="value" /></th>
                <th>Unidad</th>
                <th className="sortable" onClick={() => handleSort('effective_date')}>Fecha<SortIcon field="effective_date" /></th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {sortedObs.map((o) => (
                <tr key={o.id} className={o.is_outlier ? 'row-outlier' : ''}>
                  <td className="mono">{o.loinc_code}</td>
                  <td>{o.loinc_display || '—'}</td>
                  <td className="td-name">{o.value}</td>
                  <td>{o.unit}</td>
                  <td className="td-date">{o.effective_date?.split('T')[0] || '—'}</td>
                  <td>
                    {o.is_outlier
                      ? <span className="badge badge-danger">Outlier</span>
                      : <span className="badge badge-success">Normal</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
