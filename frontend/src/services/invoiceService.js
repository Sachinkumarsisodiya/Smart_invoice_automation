import api from './api';

export const invoiceService = {
  getInvoices: async (params = {}) => {
    const response = await api.get('/invoices', { params });
    return response.data;
  },

  getInvoice: async (id) => {
    const response = await api.get(`/invoices/${id}`);
    return response.data;
  },

  uploadInvoice: async (file, vendorId = null, onUploadProgress = null) => {
    const formData = new FormData();
    formData.append('file', file);
    if (vendorId) {
      formData.append('vendor_id', vendorId);
    }

    const response = await api.post('/invoices/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress,
    });
    return response.data;
  },

  updateInvoice: async (id, data) => {
    const response = await api.put(`/invoices/${id}`, data);
    return response.data;
  },

  deleteInvoice: async (id) => {
    const response = await api.delete(`/invoices/${id}`);
    return response.data;
  },

  extractInvoice: async (id) => {
    const response = await api.post(`/invoices/${id}/extract`);
    return response.data;
  },

  approveInvoice: async (id) => {
    const response = await api.post(`/invoices/${id}/approve`);
    return response.data;
  },

  rejectInvoice: async (id, reason = '') => {
    const response = await api.post(`/invoices/${id}/reject`, null, {
      params: reason ? { reason } : undefined,
    });
    return response.data;
  },

  getDocumentBlob: async (id) => {
    const response = await api.get(`/invoices/${id}/document`, {
      responseType: 'blob',
    });
    return response.data;
  },

  fetchFromEmail: async () => {
    const response = await api.post('/invoices/fetch-from-email');
    return response.data;
  },
};

