import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach Bearer token if present
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('smartinvoice_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle 401 Unauthorized
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
        localStorage.removeItem('smartinvoice_token');
        localStorage.removeItem('smartinvoice_user');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Invoices API helpers
export const invoiceApi = {
  sendReminder: (id) => api.post(`/invoices/${id}/send-reminder`),
};

// Vendors API
export const vendorApi = {
  list: (params) => api.get('/vendors', { params }),
  get: (id) => api.get(`/vendors/${id}`),
  create: (data) => api.post('/vendors', data),
  update: (id, data) => api.put(`/vendors/${id}`, data),
  delete: (id) => api.delete(`/vendors/${id}`),
};

// Expenses API
export const expenseApi = {
  list: (params) => api.get('/expenses', { params }),
  summary: () => api.get('/expenses/summary'),
  get: (id) => api.get(`/expenses/${id}`),
  create: (data) => api.post('/expenses', data),
  update: (id, data) => api.put(`/expenses/${id}`, data),
  delete: (id) => api.delete(`/expenses/${id}`),
};

// Payments API
export const paymentApi = {
  list: (params) => api.get('/payments', { params }),
  get: (id) => api.get(`/payments/${id}`),
  record: (data) => api.post('/payments', data),
};

// Dashboard Analytics API
export const dashboardApi = {
  getStats: () => api.get('/dashboard/stats'),
  getMonthlyCashflow: (months = 6) => api.get('/dashboard/monthly-cashflow', { params: { months } }),
  getCategoryDistribution: () => api.get('/dashboard/category-distribution'),
  getStatusDistribution: () => api.get('/dashboard/status-distribution'),
  getTopVendors: (limit = 5) => api.get('/dashboard/top-vendors', { params: { limit } }),
  getRecentActivity: (limit = 10) => api.get('/dashboard/recent-activity', { params: { limit } }),
};

// Reports & Export API
export const reportApi = {
  getTaxSummary: (params) => api.get('/reports/tax-summary', { params }),
  downloadInvoicesCsv: async (params) => {
    const res = await api.get('/reports/invoices/export', { params, responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `invoices_export_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
  downloadExpensesCsv: async (params) => {
    const res = await api.get('/reports/expenses/export', { params, responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `expenses_export_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
  downloadPaymentsCsv: async (params) => {
    const res = await api.get('/reports/payments/export', { params, responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `payments_export_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
};

// Notifications API
export const notificationApi = {
  list: (params) => api.get('/notifications', { params }),
  getUnreadCount: () => api.get('/notifications/unread-count'),
  markRead: (id) => api.put(`/notifications/${id}/read`),
  markAllRead: () => api.put('/notifications/read-all'),
  dismiss: (id) => api.delete(`/notifications/${id}`),
};

// Audit Logs API
export const auditLogApi = {
  list: (params) => api.get('/audit-logs', { params }),
};

// System Health & Automation API
export const systemApi = {
  getHealth: () => api.get('/system/health'),
  getCeleryStatus: () => api.get('/system/celery-status'),
  triggerDueDateScan: () => api.post('/system/trigger-due-date-scan'),
  triggerReminderScan: () => api.post('/system/trigger-reminder-scan'),
};

export default api;
