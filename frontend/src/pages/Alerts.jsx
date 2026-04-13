// pages/Alerts.jsx — Alertas de outliers en observaciones
import { useState, useEffect } from 'react';
import { observationsAPI } from '../services/api';
import './Alerts.css';

export default function Alerts() {
  const [outliers, setOutliers] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadOutliers(); }, []);

  const loadOutliers = async () => {
    try {
      const res = await observationsAPI.outliers();
      setOutliers(res.data.outliers || []);
      setTotal(res.data.total_outliers || 0);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="alerts-page animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Alertas Clinicas</h1>
          <p className="page-subtitle">Deteccion de valores fuera de rango (outliers)</p>
        </div>
        <button className="btn btn-secondary" onClick={loadOutliers}>
          Actualizar
        </button>
      </div>

      {loading ? (
        <div className="loading-container"><div className="spinner spinner-lg" /></div>
      ) : total > 0 ? (
        <>
          <div className="alert-banner">
            <span className="alert-banner-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            </span>
            <span>Se detectaron <strong>{total}</strong> valor(es) fuera de rango clinico</span>
          </div>
          <div className="card">
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>LOINC</th>
                    <th>Tipo</th>
                    <th>Valor</th>
                    <th>Unidad</th>
                    <th>Rango Valido</th>
                  </tr>
                </thead>
                <tbody>
                  {outliers.map((o) => (
                    <tr key={o.id} className="row-outlier">
                      <td className="mono">{o.loinc_code}</td>
                      <td>{o.loinc_display || '—'}</td>
                      <td className="td-name">{o.value}</td>
                      <td>{o.unit}</td>
                      <td className="td-range">
                        {o.range?.min} – {o.range?.max} {o.unit}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        <div className="card success-card">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--color-success)" strokeWidth="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          <h3>Todo en orden</h3>
          <p>No se detectaron outliers. Todos los valores estan dentro del rango clinico.</p>
        </div>
      )}
    </div>
  );
}
