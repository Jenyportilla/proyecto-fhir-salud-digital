// pages/Admin.jsx — Panel de administracion: usuarios CRUD con cedula, audit log, estadisticas
import { useState, useEffect } from 'react';
import { adminAPI } from '../services/api';
import './Admin.css';

export default function Admin() {
  const [tab, setTab] = useState('users');
  const [users, setUsers] = useState([]);
  const [auditLog, setAuditLog] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [sortField, setSortField] = useState('full_name');
  const [sortDir, setSortDir] = useState('asc');
  const [formData, setFormData] = useState({
    email: '', full_name: '', identification_doc: '', password: '', role: 'medico',
  });
  const [formError, setFormError] = useState('');
  const [confirmAction, setConfirmAction] = useState(null);
  const [confirmMessage, setConfirmMessage] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => { loadData(); }, [tab]);

  const loadData = async () => {
    setLoading(true);
    try {
      if (tab === 'users') {
        const res = await adminAPI.users();
        setUsers(res.data.data || []);
      } else if (tab === 'audit') {
        const res = await adminAPI.auditLog(100, 0);
        setAuditLog(res.data.data || []);
      } else if (tab === 'stats') {
        const res = await adminAPI.stats();
        setStats(res.data);
      }
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const handleSort = (field) => {
    if (sortField === field) setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDir('asc'); }
  };

  const SortIcon = ({ field }) => (
    <span className="sort-icon">
      {sortField === field ? (sortDir === 'asc' ? ' \u25B2' : ' \u25BC') : ' \u21C5'}
    </span>
  );

  const sortedUsers = [...users].sort((a, b) => {
    const aVal = a[sortField] || '';
    const bVal = b[sortField] || '';
    const cmp = String(aVal).localeCompare(String(bVal));
    return sortDir === 'asc' ? cmp : -cmp;
  });

  const openCreateForm = () => {
    setEditingUser(null);
    setFormData({ email: '', full_name: '', identification_doc: '', password: '', role: 'medico' });
    setFormError('');
    setShowForm(true);
  };

  const openEditForm = (u) => {
    setEditingUser(u);
    setFormData({
      email: u.email || '',
      full_name: u.full_name || '',
      identification_doc: u.identification_doc || '',
      password: '',
      role: u.role || 'medico',
    });
    setFormError('');
    setShowForm(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    try {
      if (editingUser) {
        const updateData = {
          full_name: formData.full_name,
          identification_doc: formData.identification_doc,
          role: formData.role,
        };
        if (formData.password) updateData.password = formData.password;
        await adminAPI.updateUser(editingUser.id, updateData);
      } else {
        await adminAPI.createUser(formData);
      }
      setShowForm(false);
      loadData();
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        const msgs = detail.map(e => `${e.loc?.slice(-1)[0] || 'campo'}: ${e.msg}`);
        setFormError(msgs.join('. '));
      } else {
        setFormError(detail || 'Error guardando usuario');
      }
    }
  };

  const requestDeleteUser = (user) => {
    setConfirmMessage(`Eliminar al usuario "${user.full_name}" (CC: ${user.identification_doc || 'N/A'})? El usuario sera removido del sistema.`);
    setConfirmAction(() => async () => {
      setActionLoading(true);
      try {
        await adminAPI.deleteUser(user.id);
        setConfirmAction(null);
        setConfirmMessage('');
        loadData();
      } catch (err) {
        alert(err.response?.data?.detail || 'Error eliminando usuario');
        setConfirmAction(null);
        setConfirmMessage('');
      } finally { setActionLoading(false); }
    });
  };

  const cancelConfirm = () => { setConfirmAction(null); setConfirmMessage(''); };

  const roleBadge = { admin: 'badge-danger', medico: 'badge-info', paciente: 'badge-success' };

  return (
    <div className="admin-page animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Administracion</h1>
        {tab === 'users' && (
          <button className="btn btn-primary" onClick={openCreateForm}>+ Nuevo Usuario</button>
        )}
      </div>

      <div className="admin-tabs">
        {['users', 'audit', 'stats'].map((t) => (
          <button key={t} className={`admin-tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {t === 'users' ? 'Usuarios' : t === 'audit' ? 'Audit Log' : 'Estadisticas'}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="loading-container"><div className="spinner spinner-lg" /></div>
      ) : (
        <div className="card">
          {tab === 'users' && (
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th className="sortable" onClick={() => handleSort('full_name')}>Nombre<SortIcon field="full_name" /></th>
                    <th className="sortable" onClick={() => handleSort('identification_doc')}>Cedula<SortIcon field="identification_doc" /></th>
                    <th className="sortable" onClick={() => handleSort('email')}>Email<SortIcon field="email" /></th>
                    <th className="sortable" onClick={() => handleSort('role')}>Rol<SortIcon field="role" /></th>
                    <th>Estado</th>
                    <th className="sortable" onClick={() => handleSort('created_at')}>Creado<SortIcon field="created_at" /></th>
                    <th className="sortable" onClick={() => handleSort('updated_at')}>Modificado<SortIcon field="updated_at" /></th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedUsers.map((u) => (
                    <tr key={u.id}>
                      <td className="td-name">{u.full_name}</td>
                      <td className="mono">{u.identification_doc || '\u2014'}</td>
                      <td>{u.email}</td>
                      <td><span className={`badge ${roleBadge[u.role]}`}>{u.role}</span></td>
                      <td>
                        <span className={`badge ${u.is_active ? 'badge-success' : 'badge-danger'}`}>
                          {u.is_active ? 'Activo' : 'Inactivo'}
                        </span>
                      </td>
                      <td className="td-date">{u.created_at?.split('T')[0] || '\u2014'}</td>
                      <td className="td-date">{u.updated_at?.split('T')[0] || '\u2014'}</td>
                      <td>
                        <div className="action-buttons">
                          <button className="btn btn-sm btn-secondary" onClick={() => openEditForm(u)}>Editar</button>
                          <button className="btn btn-sm btn-danger" onClick={() => requestDeleteUser(u)}>Eliminar</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {tab === 'audit' && (
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Accion</th>
                    <th>Usuario</th>
                    <th>Recurso</th>
                    <th>Estado</th>
                    <th>Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLog.map((entry) => (
                    <tr key={entry.id}>
                      <td className="td-name">{entry.action}</td>
                      <td>
                        <div>
                          <span style={{ fontWeight: 500 }}>{entry.user_name || '\u2014'}</span>
                          {entry.user_email && (
                            <span style={{ display: 'block', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
                              {entry.user_email}
                            </span>
                          )}
                        </div>
                      </td>
                      <td>{entry.resource_type || '\u2014'}</td>
                      <td>
                        <span className={`badge ${entry.status === 'SUCCESS' ? 'badge-success' : 'badge-danger'}`}>{entry.status}</span>
                      </td>
                      <td className="td-date">{entry.timestamp?.replace('T', ' ').split('.')[0] || '\u2014'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {auditLog.length === 0 && <p className="empty-message">No hay registros en el audit log</p>}
            </div>
          )}

          {tab === 'stats' && stats && (
            <div className="stats-detail-grid">
              <div className="stat-detail-card">
                <h4>Usuarios</h4>
                <div className="stat-detail-row"><span>Total</span><strong>{stats.users?.total}</strong></div>
                <div className="stat-detail-row"><span>Admins</span><strong>{stats.users?.admins}</strong></div>
                <div className="stat-detail-row"><span>Medicos</span><strong>{stats.users?.medicos}</strong></div>
                <div className="stat-detail-row"><span>Pacientes</span><strong>{stats.users?.pacientes}</strong></div>
              </div>
              <div className="stat-detail-card">
                <h4>Pacientes</h4>
                <div className="stat-detail-row"><span>Total</span><strong>{stats.patients?.total}</strong></div>
                <div className="stat-detail-row"><span>Activos</span><strong>{stats.patients?.active}</strong></div>
              </div>
              <div className="stat-detail-card">
                <h4>Datos Clinicos</h4>
                <div className="stat-detail-row"><span>Observaciones</span><strong>{stats.observations?.total}</strong></div>
                <div className="stat-detail-row"><span>Risk Reports</span><strong>{stats.risk_reports?.total}</strong></div>
                <div className="stat-detail-row"><span>Pendientes Firma</span><strong>{stats.risk_reports?.pending_signature}</strong></div>
              </div>
              <div className="stat-detail-card">
                <h4>Auditoria</h4>
                <div className="stat-detail-row"><span>Entradas</span><strong>{stats.audit_log?.total_entries}</strong></div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Modal Crear/Editar Usuario */}
      {showForm && (
        <div className="modal-overlay">
          <div className="modal animate-fade-in">
            <div className="modal-header">
              <h2>{editingUser ? 'Editar Usuario' : 'Nuevo Usuario'}</h2>
              <button className="modal-close" onClick={() => setShowForm(false)}>X</button>
            </div>
            <form className="modal-body" onSubmit={handleSubmit}>
              {formError && <div className="form-error">{formError}</div>}
              <div className="form-group">
                <label className="form-label">Nombre completo *</label>
                <input className="input" required value={formData.full_name}
                  onChange={(e) => setFormData({...formData, full_name: e.target.value})} />
              </div>
              <div className="form-group">
                <label className="form-label">Cedula *</label>
                <input className="input" required minLength={5} maxLength={20} placeholder="Ej: 1012345678"
                  value={formData.identification_doc}
                  onChange={(e) => setFormData({...formData, identification_doc: e.target.value})} />
              </div>
              {!editingUser && (
                <div className="form-group">
                  <label className="form-label">Email *</label>
                  <input type="email" className="input" required value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})} />
                </div>
              )}
              <div className="form-group">
                <label className="form-label">{editingUser ? 'Nueva contrasena (dejar vacio para no cambiar)' : 'Contrasena *'}</label>
                <input type="password" className="input" required={!editingUser} minLength={6}
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})} />
              </div>
              <div className="form-group">
                <label className="form-label">Rol</label>
                <select className="input" value={formData.role} onChange={(e) => setFormData({...formData, role: e.target.value})}>
                  <option value="admin">Administrador</option>
                  <option value="medico">Medico</option>
                  <option value="paciente">Paciente</option>
                </select>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Cancelar</button>
                <button type="submit" className="btn btn-primary">{editingUser ? 'Guardar Cambios' : 'Crear Usuario'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal de Confirmacion */}
      {confirmAction && (
        <div className="modal-overlay">
          <div className="modal animate-fade-in" style={{ maxWidth: 420 }}>
            <div className="modal-header">
              <h2>Confirmar accion</h2>
              <button className="modal-close" onClick={cancelConfirm}>X</button>
            </div>
            <div className="modal-body">
              <div className="confirm-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--color-warning)" strokeWidth="2">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/>
                  <line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
              </div>
              <p className="confirm-text">{confirmMessage}</p>
              <div className="modal-actions">
                <button className="btn btn-secondary" onClick={cancelConfirm} disabled={actionLoading}>Cancelar</button>
                <button className="btn btn-danger" onClick={confirmAction} disabled={actionLoading}>
                  {actionLoading ? 'Procesando...' : 'Si, eliminar'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
