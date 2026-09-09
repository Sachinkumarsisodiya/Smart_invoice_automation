import React, { useState, useEffect } from 'react';
import { 
  Building2, Plus, Search, Phone, Mail, FileText, CheckCircle2, 
  XCircle, Edit, Trash2, AlertCircle, RefreshCw, IndianRupee, 
  Clock, ShieldCheck, ExternalLink, X
} from 'lucide-react';
import { vendorApi } from '../services/api';
import { useAuth } from '../context/AuthContext';

export const Vendors = () => {
  const { hasRole } = useAuth();
  const [vendors, setVendors] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [activeOnly, setActiveOnly] = useState(false);

  // Modals & Drawers
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingVendor, setEditingVendor] = useState(null);
  const [selectedVendorDetails, setSelectedVendorDetails] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  // Form State
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    gstin: '',
    category: 'Packaging',
    payment_terms_days: 30,
    address: '',
    active: true,
  });
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  const categories = ['All', 'Packaging', 'Transport', 'Software', 'Raw Materials', 'Office', 'Electronics', 'General'];

  const fetchVendors = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {
        page: 1,
        page_size: 50,
      };
      if (search.trim()) params.search = search.trim();
      if (selectedCategory && selectedCategory !== 'All') params.category = selectedCategory;
      if (activeOnly) params.active_only = true;

      const res = await vendorApi.list(params);
      setVendors(res.data.items || []);
      setTotalCount(res.data.total || 0);
    } catch (err) {
      console.error('Failed to load vendors:', err);
      setError('Unable to load vendors. Please check backend connection.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVendors();
  }, [selectedCategory, activeOnly]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchVendors();
  };

  const handleOpenAddModal = () => {
    setEditingVendor(null);
    setFormData({
      name: '',
      email: '',
      phone: '',
      gstin: '',
      category: 'Packaging',
      payment_terms_days: 30,
      address: '',
      active: true,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (vendor, e) => {
    e.stopPropagation();
    setEditingVendor(vendor);
    setFormData({
      name: vendor.name,
      email: vendor.email || '',
      phone: vendor.phone || '',
      gstin: vendor.gstin || '',
      category: vendor.category || 'General',
      payment_terms_days: vendor.payment_terms_days || 30,
      address: vendor.address || '',
      active: vendor.active,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setFormError(null);
    setFormSubmitting(true);

    try {
      if (editingVendor) {
        await vendorApi.update(editingVendor.id, formData);
      } else {
        await vendorApi.create(formData);
      }
      setIsModalOpen(false);
      fetchVendors();
    } catch (err) {
      console.error('Save vendor failed:', err);
      setFormError(err.response?.data?.message || 'Failed to save vendor. Please check all fields.');
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleDeleteVendor = async (vendor, e) => {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete or deactivate vendor "${vendor.name}"?`)) {
      return;
    }

    try {
      await vendorApi.delete(vendor.id);
      fetchVendors();
      if (selectedVendorDetails?.id === vendor.id) {
        setSelectedVendorDetails(null);
      }
    } catch (err) {
      console.error('Delete vendor error:', err);
      alert(err.response?.data?.message || 'Could not delete vendor');
    }
  };

  const handleSelectVendor = async (vendor) => {
    try {
      setLoadingDetails(true);
      const res = await vendorApi.get(vendor.id);
      setSelectedVendorDetails(res.data);
    } catch (err) {
      console.error('Failed to get vendor details:', err);
      setSelectedVendorDetails(vendor);
    } finally {
      setLoadingDetails(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Vendor Management</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Suppliers directory, payment terms, tax registration (GSTIN), and invoice spending history.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchVendors}
            className="p-2 text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-sm"
            title="Refresh Vendors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-brand-600' : ''}`} />
          </button>
          {hasRole(['ADMIN', 'STAFF']) && (
            <button
              onClick={handleOpenAddModal}
              className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-xs font-semibold shadow-sm transition-all shadow-brand-500/20"
            >
              <Plus className="w-4 h-4" />
              <span>Add Supplier</span>
            </button>
          )}
        </div>
      </div>

      {/* KPI Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Total Suppliers</span>
          <div className="text-2xl font-bold text-slate-900 mt-1">{totalCount}</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-600">Active Status</span>
          <div className="text-2xl font-bold text-emerald-700 mt-1">
            {vendors.filter((v) => v.active).length}
          </div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-blue-600">Standard Net Terms</span>
          <div className="text-2xl font-bold text-slate-900 mt-1">30 <span className="text-xs font-normal text-slate-500">Days</span></div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-brand-600">Categories</span>
          <div className="text-2xl font-bold text-brand-700 mt-1">{new Set(vendors.map(v => v.category)).size}</div>
        </div>
      </div>

      {/* Filters Toolbar */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3">
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search vendor name, GSTIN, email..."
            className="w-full pl-9 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition"
          />
        </form>

        <div className="flex items-center gap-2 w-full md:w-auto overflow-x-auto pb-1 md:pb-0">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat === 'All' ? '' : cat)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition shrink-0 ${
                (selectedCategory === cat || (cat === 'All' && !selectedCategory))
                  ? 'bg-brand-50 text-brand-700 border border-brand-200 font-semibold'
                  : 'bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-200'
              }`}
            >
              {cat}
            </button>
          ))}
          <label className="inline-flex items-center gap-1.5 text-xs text-slate-600 ml-2 cursor-pointer shrink-0">
            <input
              type="checkbox"
              checked={activeOnly}
              onChange={(e) => setActiveOnly(e.target.checked)}
              className="rounded border-slate-300 text-brand-600 focus:ring-brand-500 w-3.5 h-3.5"
            />
            <span>Active Only</span>
          </label>
        </div>
      </div>

      {/* Vendors Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-20 bg-white rounded-xl border border-slate-200">
          <div className="flex flex-col items-center gap-2">
            <div className="w-8 h-8 border-2 border-brand-600 border-t-transparent rounded-full animate-spin"></div>
            <span className="text-xs text-slate-500">Loading suppliers...</span>
          </div>
        </div>
      ) : error ? (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 p-4 rounded-xl text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      ) : vendors.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-sm">
          <Building2 className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-slate-800">No vendors found</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
            {search || selectedCategory ? 'No vendors matched your search criteria.' : 'Create your first supplier to begin tracking invoices and payments.'}
          </p>
          {hasRole(['ADMIN', 'STAFF']) && (
            <button
              onClick={handleOpenAddModal}
              className="mt-4 inline-flex items-center gap-1.5 px-3.5 py-2 bg-brand-600 text-white rounded-lg text-xs font-semibold hover:bg-brand-500 transition"
            >
              <Plus className="w-4 h-4" />
              <span>Add Vendor</span>
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {vendors.map((vendor) => (
            <div
              key={vendor.id}
              onClick={() => handleSelectVendor(vendor)}
              className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md hover:border-brand-200 transition-all cursor-pointer group flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-slate-100 to-slate-200 border border-slate-200 flex items-center justify-center text-slate-800 font-bold text-base shadow-inner">
                      {vendor.name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 group-hover:text-brand-600 transition-colors line-clamp-1">
                        {vendor.name}
                      </h3>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-[10px] font-semibold text-brand-700 bg-brand-50 px-2 py-0.5 rounded-full border border-brand-100">
                          {vendor.category}
                        </span>
                        {vendor.active ? (
                          <span className="text-[10px] font-medium text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-100 flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Active
                          </span>
                        ) : (
                          <span className="text-[10px] font-medium text-slate-500 bg-slate-100 px-1.5 py-0.2 rounded">
                            Inactive
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {hasRole(['ADMIN', 'STAFF']) && (
                    <div className="flex items-center gap-1 opacity-80 group-hover:opacity-100 transition">
                      <button
                        onClick={(e) => handleOpenEditModal(vendor, e)}
                        className="p-1.5 text-slate-400 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition"
                        title="Edit Supplier"
                      >
                        <Edit className="w-3.5 h-3.5" />
                      </button>
                      {hasRole(['ADMIN']) && (
                        <button
                          onClick={(e) => handleDeleteVendor(vendor, e)}
                          className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
                          title="Delete / Deactivate"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  )}
                </div>

                <div className="mt-4 pt-4 border-t border-slate-100 space-y-2 text-xs text-slate-600">
                  <div className="flex items-center gap-2">
                    <Mail className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span className="truncate">{vendor.email || 'No email registered'}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Phone className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span>{vendor.phone || 'No phone recorded'}</span>
                  </div>
                  {vendor.gstin && (
                    <div className="flex items-center gap-2 text-[11px]">
                      <ShieldCheck className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
                      <span className="text-slate-500">GSTIN: <span className="font-mono text-slate-800 font-semibold">{vendor.gstin}</span></span>
                    </div>
                  )}
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                <span className="flex items-center gap-1 font-medium">
                  <Clock className="w-3 h-3 text-slate-400" /> Net {vendor.payment_terms_days} Days
                </span>
                <span className="text-brand-600 font-semibold flex items-center gap-0.5 group-hover:translate-x-0.5 transition-transform">
                  View Ledger &rarr;
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Vendor Details Drawer / Modal */}
      {selectedVendorDetails && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="p-5 bg-gradient-to-r from-slate-900 to-slate-800 text-white flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center text-lg font-bold">
                  {selectedVendorDetails.name.charAt(0)}
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">{selectedVendorDetails.name}</h3>
                  <span className="text-xs text-brand-300 font-medium">{selectedVendorDetails.category}</span>
                </div>
              </div>
              <button
                onClick={() => setSelectedVendorDetails(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-white/10 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-5">
              {/* Aggregated Financial Metrics */}
              <div className="grid grid-cols-2 gap-3 bg-slate-50 p-3.5 rounded-xl border border-slate-200">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Total Invoiced</span>
                  <div className="text-base font-bold text-slate-900 mt-0.5">
                    ₹{Number(selectedVendorDetails.total_invoiced_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </div>
                  <span className="text-[11px] text-slate-500">{selectedVendorDetails.total_invoices || 0} Invoice(s)</span>
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-amber-600">Outstanding Balance</span>
                  <div className="text-base font-bold text-amber-700 mt-0.5">
                    ₹{Number(selectedVendorDetails.outstanding_balance || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </div>
                  <span className="text-[11px] text-emerald-600 font-medium">
                    Settled: ₹{Number(selectedVendorDetails.total_paid_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </span>
                </div>
              </div>

              {/* Contact & Registration Information */}
              <div className="space-y-2.5 text-xs text-slate-700">
                <div className="flex justify-between py-1.5 border-b border-slate-100">
                  <span className="text-slate-500 font-medium">GSTIN Registration:</span>
                  <span className="font-mono font-semibold text-slate-900">{selectedVendorDetails.gstin || 'Unregistered'}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-100">
                  <span className="text-slate-500 font-medium">Email:</span>
                  <span>{selectedVendorDetails.email || 'N/A'}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-100">
                  <span className="text-slate-500 font-medium">Phone:</span>
                  <span>{selectedVendorDetails.phone || 'N/A'}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-100">
                  <span className="text-slate-500 font-medium">Payment Terms:</span>
                  <span className="font-semibold text-brand-700">Net {selectedVendorDetails.payment_terms_days} Days</span>
                </div>
                {selectedVendorDetails.address && (
                  <div className="py-1.5 border-b border-slate-100">
                    <span className="text-slate-500 font-medium block mb-0.5">Registered Address:</span>
                    <span className="text-slate-800">{selectedVendorDetails.address}</span>
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => setSelectedVendorDetails(null)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add / Edit Vendor Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <h3 className="text-sm font-bold text-slate-900">
                {editingVendor ? `Edit Supplier: ${editingVendor.name}` : 'Add New Supplier'}
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleFormSubmit} className="p-5 space-y-4">
              {formError && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{formError}</span>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Company / Vendor Name *</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g. Acme Corp Packaging Pvt Ltd"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Category</label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                  >
                    <option value="Packaging">Packaging</option>
                    <option value="Transport">Transport</option>
                    <option value="Software">Software</option>
                    <option value="Raw Materials">Raw Materials</option>
                    <option value="Office">Office</option>
                    <option value="Electronics">Electronics</option>
                    <option value="General">General</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Net Terms (Days)</label>
                  <input
                    type="number"
                    min="0"
                    max="365"
                    value={formData.payment_terms_days}
                    onChange={(e) => setFormData({ ...formData, payment_terms_days: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">GSTIN Number</label>
                  <input
                    type="text"
                    value={formData.gstin}
                    onChange={(e) => setFormData({ ...formData, gstin: e.target.value.toUpperCase() })}
                    placeholder="27AABCS1429B1Z5"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono uppercase text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Contact Phone</label>
                  <input
                    type="text"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    placeholder="+91 98765 43210"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Email Address</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="accounts@vendor.com"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Registered Address</label>
                <textarea
                  rows="2"
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  placeholder="Plot 42, Industrial Area, Phase II..."
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                ></textarea>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="vendor_active"
                  checked={formData.active}
                  onChange={(e) => setFormData({ ...formData, active: e.target.checked })}
                  className="rounded border-slate-300 text-brand-600 focus:ring-brand-500 w-4 h-4"
                />
                <label htmlFor="vendor_active" className="text-xs font-medium text-slate-700 cursor-pointer">
                  Supplier is active for new invoices
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold rounded-lg transition shadow-sm disabled:opacity-50"
                >
                  {formSubmitting ? 'Saving...' : editingVendor ? 'Update Supplier' : 'Save Supplier'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
