// pages/Observations.jsx — CRUD completo con busqueda por cedula
import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { observationsAPI, patientsAPI } from '../services/api';
import './Observations.css';

const LOINC_OPTIONS = [
  { code: '2339-0',  display: 'Glucosa', unit: 'mg/dL' },
  { code: '55284-4', display: 'Presion Arterial', unit: 'mmHg' },
  { code: '39156-5', display: 'BMI', unit: 'kg/m2' },
  { code: '14749-6', display: 'Insulina', unit: 'uU/mL' },
  { code: '8310-5',  display: 'Temperatura', unit: 'C' },
  { code: '8867-4',  display: 'Frecuencia Cardiaca', unit: 'lpm' },
];

export default function Observations() {
  const { user } = useAuth();
  const [observations, setObservations] = useState([]);
  const [patients, setPatients] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState('');
  const [filterSearch, setFilterSearch] = useState('');
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [showForm, setShowForm] = useState(false);
  const [editingObs, setEditingObs] = useState(null);
  const [sortField, setSortField] = useState('effective_date');
  const [sortDir, setSortDir] = useState('desc');

  // Form state
  const [cedulaInput, setCedulaInput] = useState('');
  const [foundPatient, setFoundPatient] = useState(null);
  const [searchingPatient, setSearchingPatient] = useState(false);
  const [cedulaError, setCedulaError] = useState('');
  const [formData, setFormData] = useState({
    loinc_code: '2339-0', loinc_display: 'Glucosa', value: '', unit: 'mg/dL',
  });
  const [formError, setFormError] = useState('');
  const LIMIT = 20;

  useEffect(() => { loadPatients(); }, []);
  useEffect(() => { loadObs(); }, [page, selectedPatient]);

  const loadPatients = async () => {
    try {
      let allPatients = [];
      let offset = 0;
      let hasMore = true;
      while (hasMore) {
        const res = await patientsAPI.list(100, offset);
        const data = res.data.data || [];
        allPatients = [...allPatients, ...data];
        if (data.length < 100 || allPatients.length >= res.data.total) hasMore = false;
        offset += 100;
      }
      setPatients(allPatients);
    } catch (err) {
      console.error('Error cargando pacientes:', err);
    }
  };

  const loadObs = async () => {
    setLoading(true);
    try {
      const res = await observationsAPI.list(selectedPatient || undefined, LIMIT, page * LIMIT);
      setObservations(res.data.data || []);
      setTotal(res.data.total || 0);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const searchByCedula = useCallback(() => {
    if (!cedulaInput.trim()) { setFoundPatient(null); setCedulaError(''); return; }
    setSearchingPatient(true);
    setCedulaError('');
    const match = patients.find((p) => p.identification_doc === cedulaInput.trim());
    if (match) { setFoundPatient(match); setCedulaError(''); }
    else { setFoundPatient(null); setCedulaError('No se encontro un paciente con esa cedula'); }
    setSearchingPatient(false);
  }, [cedulaInput, patients]);

  const handleSort = (field) => {
    if (sortField === field) setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDir('asc'); }
  };

  const sorted = [...observations].sort((a, b) => {
    let aVal = a[sortField] ?? '';
    let bVal = b[sortField] ?? '';
    if (sortField === 'value') {
      aVal = Number(aVal); bVal = Number(bVal);
      return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
    }
    const cmp = String(aVal).localeCompare(String(bVal));
    return sortDir === 'asc' ? cmp : -cmp;
  });

  const handleLoincChange = (code) => {
    const loinc = LOINC_OPTIONS.find((l) => l.code === code);
    setFormData({ ...formData, loinc_code: code, loinc_display: loinc?.display || '', unit: loinc?.unit || '' });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!foundPatient) { setCedulaError('Primero busca y selecciona un paciente valido'); return; }
    setFormError('');
    try {
      const payload = {
        patient_id: foundPatient.id,
        loinc_code: formData.loinc_code,
        loinc_display: formData.loinc_display,
        value: parseFloat(formData.value),
        unit: formData.unit,
      };
      if (editingObs) {
        await observationsAPI.update(editingObs.id, payload);
      } else {
        await observationsAPI.create(payload);
      }
      closeForm();
      loadObs();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Error guardando observacion');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Eliminar esta observacion? (soft-delete)')) return;
    try {
      await observationsAPI.delete(id);
      loadObs();
    } catch (err) {
      alert(err.response?.data?.detail || 'Error eliminando observacion');
    }
  };

  const openCreateForm = () => {
    setEditingObs(null);
    setCedulaInput('');
    setFoundPatient(null);
    setCedulaError('');
    setFormError('');
    setFormData({ loinc_code: '2339-0', loinc_display: 'Glucosa', value: '', unit: 'mg/dL' });
    setShowForm(true);
  };

  const openEditForm = (obs) => {
    setEditingObs(obs);
    // Find the patient to pre-fill the cedula
    const patient = patients.find((p) => p.id === obs.patient_id);
    if (patient) {
      setCedulaInput(patient.identification_doc || '');
      setFoundPatient(patient);
    } else {
      setCedulaInput('');
      setFoundPatient(null);
    }
    setCedulaError('');
    setFormError('');
    setFormData({
      loinc_code: obs.loinc_code,
      loinc_display: obs.loinc_display || '',
      value: String(obs.value),
      unit: obs.unit,
    });
    setShowForm(true);
  };

  const closeForm = () => {
    setShowForm(false);
    setEditingObs(null);
    setCedulaInput('');
    setFoundPatient(null);
    setCedulaError('');
    setFormError('');
  };

  const getPatientName = (patientId) => {
    const p = patients.find((pt) => pt.id === patientId);
    return p ? p.name : '';
  };

  const filteredPatients = patients.filter((p) =>
    p.name.toLowerCase().includes(filterSearch.toLowerCase()) ||
    (p.identification_doc || '').includes(filterSearch)
  );

  const totalPages = Math.ceil(total / LIMIT);
  const canCreate = user?.role === 'medico' || user?.role === 'admin';
  const canDelete = user?.role === 'admin';

  const SortIcon = ({ field }) => (
    <span className="sort-icon">
      {sortField === field ? (sortDir === 'asc' ? ' \u25B2' : ' \u25BC') : ' \u21C5'}
    </span>
  );

  return (
    <div className="observations-page animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Observaciones</h1>
          <p className="page-subtitle">{total} registros clinicos</p>
        </div>
        {canCreate && (
          <button className="btn btn-primary" onClick={openCreateForm}>
            + Nueva Observacion
          </button>
        )}
      </div>

      <div className="obs-toolbar">
        <div className="filter-search-wrapper">
          <input
            type="text"
            className="input"
            style={{ maxWidth: 300 }}
            placeholder="Buscar paciente por nombre o cedula..."
            value={filterSearch}
            onChange={(e) => setFilterSearch(e.target.value)}
          />
          {filterSearch && (
            <div className="filter-dropdown">
              <div className="filter-option" onClick={() => { setSelectedPatient(''); setFilterSearch(''); setPage(0); }}>
                Todos los pacientes
              </div>
              {filteredPatients.slice(0, 10).map((p) => (
                <div key={p.id} className="filter-option" onClick={() => { setSelectedPatient(p.id); setFilterSearch(p.name); setPage(0); }}>
                  <span className="filter-name">{p.name}</span>
                  <span className="filter-doc">{p.identification_doc}</span>
                </div>
              ))}
              {filteredPatients.length === 0 && (
                <div className="filter-option filter-empty">Sin resultados</div>
              )}
            </div>
          )}
        </div>
        {selectedPatient && (
          <button className="btn btn-sm btn-secondary" onClick={() => { setSelectedPatient(''); setFilterSearch(''); setPage(0); }}>
            Limpiar filtro
          </button>
        )}
      </div>

      <div className="card">
        {loading ? (
          <div className="loading-container"><div className="spinner spinner-lg" /></div>
        ) : (
          <>
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th className="sortable" onClick={() => handleSort('loinc_code')}>LOINC<SortIcon field="loinc_code" /></th>
                    <th className="sortable" onClick={() => handleSort('loinc_display')}>Tipo<SortIcon field="loinc_display" /></th>
                    <th className="sortable" onClick={() => handleSort('value')}>Valor<SortIcon field="value" /></th>
                    <th>Unidad</th>
                    <th>Paciente</th>
                    <th className="sortable" onClick={() => handleSort('effective_date')}>Fecha<SortIcon field="effective_date" /></th>
                    <th>Estado</th>
                    {canCreate && <th>Acciones</th>}
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((o) => (
                    <tr key={o.id} className={o.is_outlier ? 'row-outlier' : ''}>
                      <td className="mono">{o.loinc_code}</td>
                      <td>{o.loinc_display || '\u2014'}</td>
                      <td className="td-name">{o.value}</td>
                      <td>{o.unit}</td>
                      <td className="td-doctor">{getPatientName(o.patient_id) || '\u2014'}</td>
                      <td className="td-date">{o.effective_date?.split('T')[0] || '\u2014'}</td>
                      <td>
                        {o.is_outlier
                          ? <span className="badge badge-danger">Outlier</span>
                          : <span className="badge badge-success">Normal</span>}
                      </td>
                      {canCreate && (
                        <td>
                          <div className="action-buttons">
                            <button className="btn btn-sm btn-secondary" onClick={() => openEditForm(o)}>Editar</button>
                            {canDelete && (
                              <button className="btn btn-sm btn-danger" onClick={() => handleDelete(o.id)}>Eliminar</button>
                            )}
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {totalPages > 1 && (
              <div className="pagination">
                <button className="btn btn-sm btn-secondary" disabled={page === 0} onClick={() => setPage(p => p - 1)}>Anterior</button>
                <span className="page-info">Pagina {page + 1} de {totalPages}</span>
                <button className="btn btn-sm btn-secondary" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>Siguiente</button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Modal Crear/Editar Observacion */}
      {showForm && (
        <div className="modal-overlay">
          <div className="modal animate-fade-in">
            <div className="modal-header">
              <h2>{editingObs ? 'Editar Observacion' : 'Nueva Observacion'}</h2>
              <button className="modal-close" onClick={closeForm}>X</button>
            </div>
            <form className="modal-body" onSubmit={handleSubmit}>
              {formError && <div className="form-error">{formError}</div>}

              <div className="form-group">
                <label className="form-label">Cedula del paciente *</label>
                <div className="cedula-search-row">
                  <input
                    type="text"
                    className="input"
                    placeholder="Ej: 1312345678"
                    value={cedulaInput}
                    onChange={(e) => { setCedulaInput(e.target.value); setFoundPatient(null); setCedulaError(''); }}
                    onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); searchByCedula(); } }}
                  />
                  <button type="button" className="btn btn-secondary" onClick={searchByCedula} disabled={searchingPatient}>
                    Buscar
                  </button>
                </div>
                {cedulaError && <p className="form-hint form-hint-error">{cedulaError}</p>}
              </div>

              {foundPatient && (
                <div className="patient-found-card">
                  <div className="patient-found-info">
                    <span className="patient-found-name">{foundPatient.name}</span>
                    <span className="patient-found-meta">
                      {foundPatient.gender === 'male' ? 'Masculino' : foundPatient.gender === 'female' ? 'Femenino' : foundPatient.gender}
                      {' | '}{foundPatient.birth_date || 'Sin fecha'}
                      {' | CC: '}{foundPatient.identification_doc}
                    </span>
                  </div>
                  <span className="badge badge-success">Encontrado</span>
                </div>
              )}

              <div className="form-group">
                <label className="form-label">Tipo de observacion (LOINC) *</label>
                <select className="input" value={formData.loinc_code} onChange={(e) => handleLoincChange(e.target.value)}>
                  {LOINC_OPTIONS.map((l) => (
                    <option key={l.code} value={l.code}>{l.display} ({l.code})</option>
                  ))}
                </select>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Valor *</label>
                  <input
                    type="number"
                    step="0.1"
                    className="input"
                    required
                    placeholder="Ej: 120.5"
                    value={formData.value}
                    onChange={(e) => setFormData({...formData, value: e.target.value})}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Unidad</label>
                  <input className="input" readOnly value={formData.unit} />
                </div>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={closeForm}>Cancelar</button>
                <button type="submit" className="btn btn-primary" disabled={!foundPatient}>
                  {editingObs ? 'Guardar Cambios' : 'Crear Observacion'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
