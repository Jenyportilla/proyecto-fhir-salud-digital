// pages/Patients.jsx — Lista paginada con CRUD, medico asignado, ordenamiento
import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { patientsAPI } from '../services/api';
import PatientDetail from './PatientDetail';
import './Patients.css';

export default function Patients() {
  const { user } = useAuth();
  const [patients, setPatients] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(null);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingPatient, setEditingPatient] = useState(null);
  const [sortField, setSortField] = useState('name');
  const [sortDir, setSortDir] = useState('asc');
  const [formData, setFormData] = useState({
    name: '', birth_date: '', gender: '', identification_doc: '', medical_summary: '', assigned_doctor_id: '',
  });
  const [formError, setFormError] = useState('');
  const LIMIT = 10;

  useEffect(() => {
    loadPatients();
    loadDoctors();
  }, []);

  useEffect(() => { loadPatients(); }, [page]);

  const loadPatients = async () => {
    setLoading(true);
    try {
      const res = await patientsAPI.list(LIMIT, page * LIMIT);
      setPatients(res.data.data || []);
      setTotal(res.data.total || 0);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadDoctors = async () => {
    try {
      const res = await patientsAPI.doctors();
      setDoctors(res.data.data || []);
    } catch (err) {
      console.error('Error cargando medicos:', err);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Eliminar este paciente? (soft-delete)')) return;
    try {
      await patientsAPI.delete(id);
      loadPatients();
    } catch (err) {
      alert(err.response?.data?.detail || 'Error eliminando paciente');
    }
  };

  const openCreateForm = () => {
    setEditingPatient(null);
    setFormData({
      name: '', birth_date: '', gender: '', identification_doc: '', medical_summary: '',
      assigned_doctor_id: user?.role === 'medico' ? user.user_id : '',
    });
    setFormError('');
    setShowForm(true);
  };

  const openEditForm = (patient) => {
    setEditingPatient(patient);
    setFormData({
      name: patient.name || '',
      birth_date: patient.birth_date || '',
      gender: patient.gender || '',
      identification_doc: patient.identification_doc || '',
      medical_summary: patient.medical_summary || '',
      assigned_doctor_id: patient.assigned_doctor_id || '',
    });
    setFormError('');
    setShowForm(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    try {
      const data = { ...formData };
      if (!data.assigned_doctor_id) delete data.assigned_doctor_id;
      if (editingPatient) {
        await patientsAPI.update(editingPatient.id, data);
      } else {
        await patientsAPI.create(data);
      }
      setShowForm(false);
      loadPatients();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Error guardando paciente');
    }
  };

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  };

  const filtered = patients
    .filter((p) => p.name.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      const aVal = a[sortField] || '';
      const bVal = b[sortField] || '';
      const cmp = String(aVal).localeCompare(String(bVal));
      return sortDir === 'asc' ? cmp : -cmp;
    });

  const totalPages = Math.ceil(total / LIMIT);
  const canCreate = user?.role === 'admin' || user?.role === 'medico';

  const SortIcon = ({ field }) => (
    <span className="sort-icon">
      {sortField === field ? (sortDir === 'asc' ? ' \u25B2' : ' \u25BC') : ' \u21C5'}
    </span>
  );

  if (selectedId) {
    return <PatientDetail patientId={selectedId} onBack={() => { setSelectedId(null); loadPatients(); }} />;
  }

  return (
    <div className="patients-page animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Pacientes</h1>
          <p className="page-subtitle">{total} pacientes registrados</p>
        </div>
        {canCreate && (
          <button className="btn btn-primary" onClick={openCreateForm}>
            + Nuevo Paciente
          </button>
        )}
      </div>

      <div className="patients-toolbar">
        <input
          type="text"
          className="input search-input"
          placeholder="Buscar paciente..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
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
                    <th className="sortable" onClick={() => handleSort('name')}>Nombre<SortIcon field="name" /></th>
                    <th className="sortable" onClick={() => handleSort('gender')}>Genero<SortIcon field="gender" /></th>
                    <th className="sortable" onClick={() => handleSort('birth_date')}>Fecha Nac.<SortIcon field="birth_date" /></th>
                    <th>Documento</th>
                    <th className="sortable" onClick={() => handleSort('assigned_doctor_name')}>Medico<SortIcon field="assigned_doctor_name" /></th>
                    <th className="sortable" onClick={() => handleSort('status')}>Estado<SortIcon field="status" /></th>
                    <th className="sortable" onClick={() => handleSort('created_at')}>Creado<SortIcon field="created_at" /></th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((p) => (
                    <tr key={p.id}>
                      <td className="td-name clickable" onClick={() => setSelectedId(p.id)}>{p.name}</td>
                      <td>{p.gender === 'male' ? 'M' : p.gender === 'female' ? 'F' : '\u2014'}</td>
                      <td>{p.birth_date || '\u2014'}</td>
                      <td className="td-doc">{p.identification_doc === 'Oculto' ? 'Oculto' : p.identification_doc}</td>
                      <td className="td-doctor">{p.assigned_doctor_name || 'Sin asignar'}</td>
                      <td>
                        <span className={`badge ${p.status === 'active' ? 'badge-success' : 'badge-warning'}`}>
                          {p.status}
                        </span>
                      </td>
                      <td className="td-date">{p.created_at?.split('T')[0] || '\u2014'}</td>
                      <td>
                        <div className="action-buttons">
                          <button className="btn btn-sm btn-secondary" onClick={() => setSelectedId(p.id)}>Ver</button>
                          {canCreate && (
                            <button className="btn btn-sm btn-secondary" onClick={() => openEditForm(p)}>Editar</button>
                          )}
                          {user?.role === 'admin' && (
                            <button className="btn btn-sm btn-danger" onClick={() => handleDelete(p.id)}>Eliminar</button>
                          )}
                        </div>
                      </td>
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

      {/* Modal Crear/Editar Paciente */}
      {showForm && (
        <div className="modal-overlay">
          <div className="modal animate-fade-in">
            <div className="modal-header">
              <h2>{editingPatient ? 'Editar Paciente' : 'Nuevo Paciente'}</h2>
              <button className="modal-close" onClick={() => setShowForm(false)}>X</button>
            </div>
            <form className="modal-body" onSubmit={handleSubmit}>
              {formError && <div className="form-error">{formError}</div>}
              <div className="form-group">
                <label className="form-label">Nombre completo *</label>
                <input className="input" required value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value})} />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Fecha de nacimiento</label>
                  <input type="date" className="input" value={formData.birth_date} onChange={(e) => setFormData({...formData, birth_date: e.target.value})} />
                </div>
                <div className="form-group">
                  <label className="form-label">Genero</label>
                  <select className="input" value={formData.gender} onChange={(e) => setFormData({...formData, gender: e.target.value})}>
                    <option value="">Seleccionar</option>
                    <option value="male">Masculino</option>
                    <option value="female">Femenino</option>
                    <option value="other">Otro</option>
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Documento de identidad *</label>
                <input className="input" required value={formData.identification_doc} onChange={(e) => setFormData({...formData, identification_doc: e.target.value})} />
              </div>
              <div className="form-group">
                <label className="form-label">Medico asignado</label>
                <select
                  className="input"
                  value={formData.assigned_doctor_id}
                  onChange={(e) => setFormData({...formData, assigned_doctor_id: e.target.value})}
                  disabled={user?.role === 'medico'}
                >
                  <option value="">Sin asignar</option>
                  {doctors.map((d) => (
                    <option key={d.id} value={d.id}>{d.full_name} ({d.email})</option>
                  ))}
                </select>
                {user?.role === 'medico' && (
                  <p className="form-hint">Los pacientes se asignan automaticamente a ti</p>
                )}
              </div>
              <div className="form-group">
                <label className="form-label">Resumen medico</label>
                <textarea className="input textarea" rows="3" value={formData.medical_summary} onChange={(e) => setFormData({...formData, medical_summary: e.target.value})} />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Cancelar</button>
                <button type="submit" className="btn btn-primary">{editingPatient ? 'Guardar Cambios' : 'Crear Paciente'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
