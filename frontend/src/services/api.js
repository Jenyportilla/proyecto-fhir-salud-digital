// services/api.js — Servicio HTTP centralizado para comunicación con el backend
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Interceptor: inyectar API Keys + JWT en cada request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  const accessKey = localStorage.getItem('accessKey') || 'master-access-key';
  const permissionKey = localStorage.getItem('permissionKey') || 'admin-permission';

  if (token) config.headers.Authorization = `Bearer ${token}`;
  config.headers['X-Access-Key'] = accessKey;
  config.headers['X-Permission-Key'] = permissionKey;

  return config;
});

// Interceptor: manejar errores de auth
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.clear();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ── AUTH ──
export const authAPI = {
  login: (email, password) =>
    api.post('/auth/login', { email, password }),
  me: () => api.get('/auth/me'),
  habeasData: (accepted) =>
    api.post('/auth/habeas-data', { accepted }),
  logout: () => api.post('/auth/logout'),
};

// ── PATIENTS ──
export const patientsAPI = {
  list: (limit = 10, offset = 0) =>
    api.get('/fhir/Patient', { params: { limit, offset } }),
  get: (id) => api.get(`/fhir/Patient/${id}`),
  create: (data) => api.post('/fhir/Patient', data),
  update: (id, data) => api.patch(`/fhir/Patient/${id}`, data),
  delete: (id) => api.delete(`/fhir/Patient/${id}`),
  restore: (id) => api.patch(`/fhir/Patient/${id}/restore`),
  canClose: (id) => api.get(`/fhir/Patient/${id}/can-close`),
  doctors: () => api.get('/fhir/Patient/doctors'),
  pendingReports: () => api.get('/fhir/Patient/pending-reports'),
  riskReports: (patientId) =>
    api.get(`/fhir/Patient/${patientId}/risk-reports`),
  signReport: (patientId, reportId, data) =>
    api.patch(`/fhir/Patient/${patientId}/risk-reports/${reportId}/sign`, data),
};

// ── OBSERVATIONS ──
export const observationsAPI = {
  list: (patientId, limit = 50, offset = 0) =>
    api.get('/fhir/Observation', { params: { patient_id: patientId, limit, offset } }),
  create: (data) => api.post('/fhir/Observation', data),
  update: (id, data) => api.patch(`/fhir/Observation/${id}`, data),
  delete: (id) => api.delete(`/fhir/Observation/${id}`),
  outliers: () => api.get('/fhir/Observation/outliers'),
};

// ── IMAGES (MinIO) ──
export const imagesAPI = {
  listByPatient: (patientId) =>
    api.get(`/fhir/Media/patient/${patientId}`),
  get: (id) => api.get(`/fhir/Media/${id}`),
  upload: (patientId, modality, description, file) => {
    const formData = new FormData();
    formData.append('patient_id', patientId);
    formData.append('modality', modality);
    if (description) formData.append('description', description);
    formData.append('file', file);
    return api.post('/fhir/Media', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  delete: (id) => api.delete(`/fhir/Media/${id}`),
};

// ── ADMIN ──
export const adminAPI = {
  users: (limit = 50, offset = 0) =>
    api.get('/admin/users', { params: { limit, offset } }),
  createUser: (data) => api.post('/admin/users', data),
  updateUser: (id, data) => api.patch(`/admin/users/${id}`, data),
  deleteUser: (id) => api.delete(`/admin/users/${id}`),
  auditLog: (limit = 50, offset = 0, action, userId, dateFrom, dateTo) =>
    api.get('/admin/audit-log', { params: { limit, offset, action, user_id: userId, date_from: dateFrom, date_to: dateTo } }),
  exportAuditLog: (format = 'json', action) =>
    api.get('/admin/audit-log/export', { params: { format, action } }),
  stats: () => api.get('/admin/stats'),
};

// ── INFERENCE (ML/DL) ──
export const inferenceAPI = {
  runML: (patientId, features) =>
    api.post('/inference/ml', { patient_id: patientId, features }),
  runDL: (patientId, imageUrl) =>
    api.post('/inference/dl', { patient_id: patientId, image_url: imageUrl }),
  status: (taskId) =>
    api.get(`/inference/status/${taskId}`),
};

export default api;
