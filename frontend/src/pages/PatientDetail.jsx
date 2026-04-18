// pages/PatientDetail.jsx — Ficha clinica con observaciones, reportes, imagenes y firma
import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { observationsAPI, patientsAPI, imagesAPI, inferenceAPI } from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import './PatientDetail.css';

export default function PatientDetail({ patientId, onBack }) {
  const { user } = useAuth();
  const [patient, setPatient] = useState(null);
  const [observations, setObservations] = useState([]);
  const [riskReports, setRiskReports] = useState([]);
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('observations');
  const [sortField, setSortField] = useState('effective_date');
  const [sortDir, setSortDir] = useState('desc');

  // Sign Report Modal
  const [showSignModal, setShowSignModal] = useState(false);
  const [selectedReport, setSelectedReport] = useState(null);
  const [signForm, setSignForm] = useState({ clinical_notes: '', action: 'ACCEPT', justification: '' });
  const [signError, setSignError] = useState('');
  const [signLoading, setSignLoading] = useState(false);

  // Upload Image Modal
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadForm, setUploadForm] = useState({ modality: 'OTHER', description: '', file: null });
  const [uploadError, setUploadError] = useState('');
  const [uploadLoading, setUploadLoading] = useState(false);

  // Lightbox
  const [lightboxImage, setLightboxImage] = useState(null);

  // Inference ML
  const [mlTaskId, setMlTaskId] = useState(null);
  const [mlResult, setMlResult] = useState(null);
  const [mlLoading, setMlLoading] = useState(false);
  const [mlError, setMlError] = useState('');

  // Inference DL
  const [dlTaskId, setDlTaskId] = useState(null);
  const [dlResult, setDlResult] = useState(null);
  const [dlLoading, setDlLoading] = useState(false);
  const [dlError, setDlError] = useState('');

  useEffect(() => { loadData(); }, [patientId]);

  const loadData = async () => {
    try {
      const [patRes, obsRes] = await Promise.all([
        patientsAPI.get(patientId),
        observationsAPI.list(patientId, 100, 0),
      ]);
      setPatient(patRes.data);
      setObservations(obsRes.data.data || []);

      // Cargar imagenes (toleramos error si MinIO no esta)
      try {
        const imgRes = await imagesAPI.listByPatient(patientId);
        setImages(imgRes.data.data || []);
      } catch (e) {
        setImages([]);
      }

      // Cargar RiskReports
      try {
        const repRes = await patientsAPI.riskReports(patientId);
        setRiskReports(repRes.data.data || []);
      } catch (e) {
        setRiskReports([]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // ── FIRMA DE RISK REPORT ──
  const openSignModal = (report) => {
    setSelectedReport(report);
    setSignForm({ clinical_notes: '', action: 'ACCEPT', justification: '' });
    setSignError('');
    setShowSignModal(true);
  };

  const handleSign = async (e) => {
    e.preventDefault();
    setSignError('');
    setSignLoading(true);
    try {
      const data = {
        clinical_notes: signForm.clinical_notes,
        action: signForm.action,
      };
      if (signForm.action === 'REJECT') {
        data.justification = signForm.justification;
      }
      await patientsAPI.signReport(patientId, selectedReport.id, data);
      setShowSignModal(false);
      loadData();
    } catch (err) {
      setSignError(err.response?.data?.detail || 'Error firmando el reporte');
    } finally {
      setSignLoading(false);
    }
  };

  // ── SUBIR IMAGEN ──
  const handleUpload = async (e) => {
    e.preventDefault();
    setUploadError('');
    setUploadLoading(true);
    try {
      await imagesAPI.upload(patientId, uploadForm.modality, uploadForm.description, uploadForm.file);
      setShowUploadModal(false);
      setUploadForm({ modality: 'OTHER', description: '', file: null });
      loadData();
    } catch (err) {
      setUploadError(err.response?.data?.detail || 'Error subiendo imagen');
    } finally {
      setUploadLoading(false);
    }
  };

  // ── SORTING ──
  const handleSort = (field) => {
    if (sortField === field) setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDir('asc'); }
  };

  const SortIcon = ({ field }) => (
    <span className="sort-icon">
      {sortField === field ? (sortDir === 'asc' ? ' \u25B2' : ' \u25BC') : ' \u21C5'}
    </span>
  );

  if (loading) {
    return <div className="loading-container"><div className="spinner spinner-lg" /></div>;
  }

  // Agrupar observaciones para graficas
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
  const canSign = user?.role === 'medico' || user?.role === 'admin';
  const canUpload = user?.role === 'medico' || user?.role === 'admin';

  return (
    <div className="patient-detail animate-fade-in">
      <button className="btn btn-secondary btn-sm" onClick={onBack}>
        ← Volver a pacientes
      </button>

      {/* Header del paciente */}
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
              <span className="meta-value">{patient?.gender === 'male' ? 'Masculino' : patient?.gender === 'female' ? 'Femenino' : '—'}</span>
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
              <span className="meta-label">Medico asignado</span>
              <span className="meta-value">{patient?.assigned_doctor_name || 'Sin asignar'}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Resumen medico</span>
              <span className="meta-value">{patient?.medical_summary || '—'}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Creado</span>
              <span className="meta-value">{patient?.created_at?.split('T')[0] || '—'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="detail-tabs">
        <button
          className={`tab-btn ${activeTab === 'observations' ? 'active' : ''}`}
          onClick={() => setActiveTab('observations')}
        >
          Observaciones ({observations.length})
        </button>
        <button
          className={`tab-btn ${activeTab === 'reports' ? 'active' : ''}`}
          onClick={() => setActiveTab('reports')}
        >
          Reportes de Riesgo ({riskReports.length})
        </button>
        <button
          className={`tab-btn ${activeTab === 'images' ? 'active' : ''}`}
          onClick={() => setActiveTab('images')}
        >
          Imagenes ({images.length})
        </button>
        {canSign && (
          <>
            <button
              className={`tab-btn ${activeTab === 'ml' ? 'active' : ''}`}
              onClick={() => setActiveTab('ml')}
            >
              Analisis ML
            </button>
            <button
              className={`tab-btn ${activeTab === 'dl' ? 'active' : ''}`}
              onClick={() => setActiveTab('dl')}
            >
              Analisis DL
            </button>
          </>
        )}
      </div>

      {/* Tab: Observaciones */}
      {activeTab === 'observations' && (
        <>
          {/* Graficas */}
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

          {/* Tabla de Observaciones */}
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
        </>
      )}

      {/* Tab: Reportes de Riesgo */}
      {activeTab === 'reports' && (
        <div className="card">
          <h3 className="section-title">Reportes de Riesgo (RiskAssessment)</h3>
          {riskReports.length > 0 ? (
            <div className="reports-grid">
              {riskReports.map((r) => (
                <div key={r.id} className={`report-card ${r.signed_at ? 'signed' : 'pending'}`}>
                  <div className="report-info">
                    <span className={`badge ${r.model_type === 'ML' ? 'badge-info' : 'badge-warning'}`}>{r.model_type}</span>
                    <span className="report-score">{r.risk_score != null ? `${(r.risk_score * 100).toFixed(0)}%` : '—'}</span>
                    <span className={`badge ${
                      r.risk_category === 'CRITICAL' ? 'badge-danger' :
                      r.risk_category === 'HIGH' ? 'badge-warning' :
                      r.risk_category === 'MEDIUM' ? 'badge-info' :
                      'badge-success'
                    }`}>{r.risk_category}</span>
                    <span className="report-date">{r.created_at?.split('T')[0]}</span>
                  </div>
                  <div className="report-actions">
                    {r.signed_at ? (
                      <span className="badge badge-success">Firmado ({r.feedback})</span>
                    ) : (
                      canSign && (
                        <button className="btn btn-primary btn-sm" onClick={() => openSignModal(r)}>
                          Firmar
                        </button>
                      )
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="empty-message">No hay reportes de riesgo para este paciente</p>
          )}
        </div>
      )}

      {/* Tab: Imagenes */}
      {activeTab === 'images' && (
        <div className="card">
          <div className="section-header">
            <h3 className="section-title">Imagenes Medicas (MinIO)</h3>
            {canUpload && (
              <button className="btn btn-primary btn-sm" onClick={() => setShowUploadModal(true)}>
                + Subir Imagen
              </button>
            )}
          </div>

          {images.length > 0 ? (
            <div className="images-grid">
              {images.map((img) => (
                <div key={img.id} className="image-card">
                  <div
                    className="image-preview clickable"
                    onClick={() => img.presigned_url && setLightboxImage(img)}
                    title="Clic para ver en grande"
                  >
                    {img.presigned_url ? (
                      <img src={img.presigned_url} alt={img.original_filename} loading="lazy" />
                    ) : (
                      <div className="image-placeholder">
                        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>
                        </svg>
                        <span>MinIO no disponible</span>
                      </div>
                    )}
                    {img.presigned_url && (
                      <div className="image-overlay">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                          <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/>
                        </svg>
                      </div>
                    )}
                  </div>
                  <div className="image-info">
                    <span className="badge badge-info">{img.modality}</span>
                    <p className="image-filename">{img.original_filename}</p>
                    {img.description && <p className="image-desc">{img.description}</p>}
                    <p className="image-date">{img.created_at?.split('T')[0]}</p>
                    <div className="image-actions">
                      {img.presigned_url && (
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => window.open(img.presigned_url, '_blank')}
                        >
                          Abrir
                        </button>
                      )}
                      {canUpload && (
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={async () => {
                            if (!confirm('Eliminar esta imagen?')) return;
                            try {
                              await imagesAPI.delete(img.id);
                              loadData();
                            } catch (err) {
                              alert(err.response?.data?.detail || 'Error eliminando imagen');
                            }
                          }}
                        >
                          Eliminar
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="empty-message">No hay imagenes para este paciente</p>
          )}
        </div>
      )}

      {/* Tab: Analisis ML */}
      {activeTab === 'ml' && (
        <div className="card">
          <h3 className="section-title">Analisis ML — Prediccion de Riesgo (SHAP)</h3>
          <p style={{color:'var(--color-text-muted)',fontSize:'var(--text-sm)',marginBottom:'16px'}}>
            Ejecuta el modelo tabular ONNX para evaluar el riesgo de diabetes basado en las observaciones del paciente.
          </p>
          <button
            className="btn btn-primary"
            disabled={mlLoading}
            onClick={async () => {
              setMlLoading(true); setMlError(''); setMlResult(null);
              try {
                // Extraer features de las observaciones del paciente
                const featureMap = {};
                const loincToFeature = {
                  '2339-0': 'Glucose', '55284-4': 'BloodPressure',
                  '39156-5': 'BMI', '14749-6': 'Insulin',
                  '30525-0': 'Age',
                };
                observations.forEach(o => {
                  const feat = loincToFeature[o.loinc_code];
                  if (feat) featureMap[feat] = o.value;
                });
                // Defaults
                if (!featureMap.Glucose) featureMap.Glucose = 120;
                if (!featureMap.BloodPressure) featureMap.BloodPressure = 80;
                if (!featureMap.BMI) featureMap.BMI = 28;
                if (!featureMap.Insulin) featureMap.Insulin = 85;
                if (!featureMap.Age) featureMap.Age = 45;
                featureMap.Pregnancies = featureMap.Pregnancies || 2;
                featureMap.SkinThickness = featureMap.SkinThickness || 25;
                featureMap.DiabetesPedigreeFunction = featureMap.DiabetesPedigreeFunction || 0.45;

                const res = await inferenceAPI.runML(patientId, featureMap);
                const taskId = res.data.task_id;
                setMlTaskId(taskId);
                // Polling
                const poll = setInterval(async () => {
                  try {
                    const st = await inferenceAPI.status(taskId);
                    if (st.data.status === 'DONE') {
                      clearInterval(poll);
                      setMlResult(st.data.result);
                      setMlLoading(false);
                      loadData();
                    } else if (st.data.status === 'ERROR') {
                      clearInterval(poll);
                      setMlError(st.data.error || 'Error en inferencia');
                      setMlLoading(false);
                    }
                  } catch { clearInterval(poll); setMlError('Error consultando estado'); setMlLoading(false); }
                }, 1500);
              } catch (err) {
                setMlError(err.response?.data?.detail || 'Error lanzando inferencia');
                setMlLoading(false);
              }
            }}
          >
            {mlLoading ? <><span className="spinner" /> Ejecutando modelo...</> : 'Ejecutar Analisis ML'}
          </button>

          {mlError && <div className="form-error" style={{marginTop:'12px'}}>{mlError}</div>}

          {mlResult && (
            <div className="ml-result" style={{marginTop:'20px'}}>
              <div style={{display:'flex',gap:'16px',flexWrap:'wrap',marginBottom:'16px'}}>
                <div className="stat-card">
                  <span className="stat-label">Probabilidad</span>
                  <span className="stat-number">{(mlResult.probability * 100).toFixed(1)}%</span>
                </div>
                <div className="stat-card">
                  <span className="stat-label">Categoria</span>
                  <span className={`badge ${
                    mlResult.risk_category === 'CRITICAL' ? 'badge-danger' :
                    mlResult.risk_category === 'HIGH' ? 'badge-warning' :
                    mlResult.risk_category === 'MEDIUM' ? 'badge-info' : 'badge-success'
                  }`}>{mlResult.risk_category}</span>
                </div>
                <div className="stat-card">
                  <span className="stat-label">Calibracion</span>
                  <span style={{color:'var(--color-text-muted)',fontSize:'var(--text-sm)'}}>{mlResult.calibration || 'isotonic'}</span>
                </div>
              </div>

              {/* SHAP Bar Chart */}
              {mlResult.shap_values && (
                <div>
                  <h4 style={{marginBottom:'12px',color:'var(--color-text-primary)'}}>Explicabilidad SHAP</h4>
                  <div className="shap-chart">
                    {Object.entries(mlResult.shap_values)
                      .sort(([,a],[,b]) => Math.abs(b) - Math.abs(a))
                      .map(([feat, val]) => {
                        const maxVal = Math.max(...Object.values(mlResult.shap_values).map(Math.abs));
                        const pct = maxVal > 0 ? (Math.abs(val) / maxVal * 100) : 0;
                        const isPositive = val > 0;
                        return (
                          <div key={feat} className="shap-row">
                            <span className="shap-label">{feat}</span>
                            <div className="shap-bar-container">
                              <div className="shap-bar-bg">
                                <div
                                  className={`shap-bar ${isPositive ? 'shap-positive' : 'shap-negative'}`}
                                  style={{ width: `${Math.max(pct, 3)}%` }}
                                />
                              </div>
                              <span className="shap-value">{val > 0 ? '+' : ''}{val.toFixed(4)}</span>
                            </div>
                          </div>
                        );
                      })
                    }
                  </div>
                  <p style={{fontSize:'var(--text-xs)',color:'var(--color-text-muted)',marginTop:'8px'}}>
                    Rojo = incrementa riesgo | Azul = reduce riesgo
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab: Analisis DL */}
      {activeTab === 'dl' && (
        <div className="card">
          <h3 className="section-title">Analisis DL — Retinopatia Diabetica (Grad-CAM)</h3>
          <p style={{color:'var(--color-text-muted)',fontSize:'var(--text-sm)',marginBottom:'16px'}}>
            Selecciona una imagen de fondo de ojo para ejecutar el modelo de deteccion de retinopatia.
          </p>

          {images.length > 0 ? (
            <div>
              <div style={{display:'flex',gap:'8px',flexWrap:'wrap',marginBottom:'16px'}}>
                {images.filter(i => i.presigned_url).map(img => (
                  <button
                    key={img.id}
                    className="btn btn-secondary btn-sm"
                    disabled={dlLoading}
                    onClick={async () => {
                      setDlLoading(true); setDlError(''); setDlResult(null);
                      try {
                        const res = await inferenceAPI.runDL(patientId, img.presigned_url);
                        const taskId = res.data.task_id;
                        setDlTaskId(taskId);
                        const poll = setInterval(async () => {
                          try {
                            const st = await inferenceAPI.status(taskId);
                            if (st.data.status === 'DONE') {
                              clearInterval(poll);
                              setDlResult({ ...st.data.result, original_url: img.presigned_url });
                              setDlLoading(false);
                              loadData();
                            } else if (st.data.status === 'ERROR') {
                              clearInterval(poll);
                              setDlError(st.data.error || 'Error en inferencia');
                              setDlLoading(false);
                            }
                          } catch { clearInterval(poll); setDlError('Error consultando estado'); setDlLoading(false); }
                        }, 2000);
                      } catch (err) {
                        setDlError(err.response?.data?.detail || 'Error lanzando inferencia');
                        setDlLoading(false);
                      }
                    }}
                  >
                    {img.original_filename || 'Imagen'}
                  </button>
                ))}
              </div>
              {dlLoading && <div style={{textAlign:'center',padding:'20px'}}><span className="spinner spinner-lg" /> <p>Analizando imagen...</p></div>}
              {dlError && <div className="form-error">{dlError}</div>}

              {dlResult && (
                <div className="dl-result">
                  <div style={{display:'flex',gap:'16px',flexWrap:'wrap',marginBottom:'16px'}}>
                    <div className="stat-card">
                      <span className="stat-label">Severidad</span>
                      <span className="stat-number">{dlResult.severity_label}</span>
                    </div>
                    <div className="stat-card">
                      <span className="stat-label">Confianza</span>
                      <span className="stat-number">{(dlResult.confidence * 100).toFixed(1)}%</span>
                    </div>
                    <div className="stat-card">
                      <span className="stat-label">Categoria</span>
                      <span className={`badge ${
                        dlResult.risk_category === 'CRITICAL' ? 'badge-danger' :
                        dlResult.risk_category === 'HIGH' ? 'badge-warning' :
                        dlResult.risk_category === 'MEDIUM' ? 'badge-info' : 'badge-success'
                      }`}>{dlResult.risk_category}</span>
                    </div>
                  </div>

                  {/* Imagen original vs Grad-CAM */}
                  <h4 style={{marginBottom:'12px',color:'var(--color-text-primary)'}}>Comparacion: Original vs Grad-CAM</h4>
                  <div className="gradcam-compare">
                    <div className="gradcam-panel">
                      <h5>Original</h5>
                      <img src={dlResult.original_url} alt="Original" />
                    </div>
                    <div className="gradcam-panel">
                      <h5>Grad-CAM</h5>
                      {dlResult.gradcam_url ? (
                        <img src={dlResult.gradcam_url} alt="Grad-CAM" />
                      ) : (
                        <p style={{color:'var(--color-text-muted)'}}>Grad-CAM no disponible</p>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="empty-message">Sube una imagen de fondo de ojo en la pestana "Imagenes" primero</p>
          )}
        </div>
      )}

      {/* Modal: Firma de RiskReport */}
      {showSignModal && selectedReport && (
        <div className="modal-overlay">
          <div className="modal animate-fade-in modal-lg">
            <div className="modal-header">
              <h2>Firmar Reporte de Riesgo</h2>
              <button className="modal-close" onClick={() => setShowSignModal(false)}>X</button>
            </div>
            <form className="modal-body" onSubmit={handleSign}>
              {signError && <div className="form-error">{signError}</div>}

              <div className="report-summary">
                <div className="report-meta">
                  <span className="meta-label">Modelo:</span>
                  <span className="badge badge-info">{selectedReport.model_type}</span>
                </div>
                {selectedReport.risk_score != null && (
                  <div className="report-meta">
                    <span className="meta-label">Score de Riesgo:</span>
                    <span className="risk-score">{(selectedReport.risk_score * 100).toFixed(1)}%</span>
                  </div>
                )}
                {selectedReport.risk_category && (
                  <div className="report-meta">
                    <span className="meta-label">Categoria:</span>
                    <span className={`badge ${
                      selectedReport.risk_category === 'CRITICAL' ? 'badge-danger' :
                      selectedReport.risk_category === 'HIGH' ? 'badge-warning' :
                      'badge-success'
                    }`}>{selectedReport.risk_category}</span>
                  </div>
                )}
              </div>

              <div className="form-group">
                <label className="form-label">Observaciones clinicas * (minimo 30 caracteres)</label>
                <textarea
                  className="input textarea"
                  rows="4"
                  required
                  minLength={30}
                  placeholder="Escriba sus observaciones clinicas sobre este resultado..."
                  value={signForm.clinical_notes}
                  onChange={(e) => setSignForm({...signForm, clinical_notes: e.target.value})}
                />
                <span className="char-count">{signForm.clinical_notes.length}/30 caracteres minimos</span>
              </div>

              <div className="form-group">
                <label className="form-label">Decision *</label>
                <div className="action-selector">
                  <label className={`action-option ${signForm.action === 'ACCEPT' ? 'selected accept' : ''}`}>
                    <input
                      type="radio" name="action" value="ACCEPT"
                      checked={signForm.action === 'ACCEPT'}
                      onChange={(e) => setSignForm({...signForm, action: e.target.value})}
                    />
                    <span className="action-label">ACEPTAR resultado</span>
                  </label>
                  <label className={`action-option ${signForm.action === 'REJECT' ? 'selected reject' : ''}`}>
                    <input
                      type="radio" name="action" value="REJECT"
                      checked={signForm.action === 'REJECT'}
                      onChange={(e) => setSignForm({...signForm, action: e.target.value})}
                    />
                    <span className="action-label">RECHAZAR resultado</span>
                  </label>
                </div>
              </div>

              {signForm.action === 'REJECT' && (
                <div className="form-group">
                  <label className="form-label">Justificacion del rechazo * (minimo 20 caracteres)</label>
                  <textarea
                    className="input textarea"
                    rows="3"
                    required
                    minLength={20}
                    placeholder="Justifique por que rechaza este resultado..."
                    value={signForm.justification}
                    onChange={(e) => setSignForm({...signForm, justification: e.target.value})}
                  />
                  <span className="char-count">{signForm.justification.length}/20 caracteres minimos</span>
                </div>
              )}

              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowSignModal(false)}>Cancelar</button>
                <button type="submit" className={`btn ${signForm.action === 'ACCEPT' ? 'btn-primary' : 'btn-danger'}`} disabled={signLoading}>
                  {signLoading ? <span className="spinner" /> : `Firmar y ${signForm.action === 'ACCEPT' ? 'Aceptar' : 'Rechazar'}`}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Subir Imagen */}
      {showUploadModal && (
        <div className="modal-overlay">
          <div className="modal animate-fade-in">
            <div className="modal-header">
              <h2>Subir Imagen Medica</h2>
              <button className="modal-close" onClick={() => setShowUploadModal(false)}>X</button>
            </div>
            <form className="modal-body" onSubmit={handleUpload}>
              {uploadError && <div className="form-error">{uploadError}</div>}

              <div className="form-group">
                <label className="form-label">Modalidad *</label>
                <select className="input" value={uploadForm.modality} onChange={(e) => setUploadForm({...uploadForm, modality: e.target.value})}>
                  <option value="FUNDUS">Fondo de ojo (FUNDUS)</option>
                  <option value="XRAY">Radiografia (XRAY)</option>
                  <option value="DERM">Dermatologia (DERM)</option>
                  <option value="CT">Tomografia (CT)</option>
                  <option value="MRI">Resonancia (MRI)</option>
                  <option value="US">Ecografia (US)</option>
                  <option value="OTHER">Otra</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Descripcion</label>
                <textarea
                  className="input textarea"
                  rows="2"
                  placeholder="Descripcion clinica de la imagen..."
                  value={uploadForm.description}
                  onChange={(e) => setUploadForm({...uploadForm, description: e.target.value})}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Archivo de imagen *</label>
                <input
                  type="file"
                  className="input"
                  accept="image/*"
                  required
                  onChange={(e) => setUploadForm({...uploadForm, file: e.target.files[0]})}
                />
                <p className="form-hint">Formatos: JPEG, PNG, DICOM. Max 10MB</p>
              </div>

              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowUploadModal(false)}>Cancelar</button>
                <button type="submit" className="btn btn-primary" disabled={uploadLoading}>
                  {uploadLoading ? <span className="spinner" /> : 'Subir Imagen'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* Lightbox: Vista previa de imagen */}
      {lightboxImage && (
        <div className="lightbox-overlay" onClick={() => setLightboxImage(null)}>
          <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
            <div className="lightbox-header">
              <div className="lightbox-title">
                <span className="badge badge-info">{lightboxImage.modality}</span>
                <span>{lightboxImage.original_filename}</span>
              </div>
              <div className="lightbox-actions">
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => window.open(lightboxImage.presigned_url, '_blank')}
                >
                  Abrir en nueva ventana
                </button>
                <button className="lightbox-close" onClick={() => setLightboxImage(null)}>X</button>
              </div>
            </div>
            <div className="lightbox-image">
              <img src={lightboxImage.presigned_url} alt={lightboxImage.original_filename} />
            </div>
            {lightboxImage.description && (
              <p className="lightbox-desc">{lightboxImage.description}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
