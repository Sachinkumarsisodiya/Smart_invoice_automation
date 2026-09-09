import React, { useState, useEffect } from 'react';
import { 
  Receipt, Plus, Filter, Calendar, Search, Trash2, Edit, 
  AlertCircle, RefreshCw, CreditCard, PieChart, IndianRupee, X
} from 'lucide-react';
import { expenseApi, vendorApi } from '../services/api';
import { useAuth } from '../context/AuthContext';

export const Expenses = () => {
  const { hasRole } = useAuth();
  const [expenses, setExpenses] = useState([]);
  const [summary, setSummary] = useState(null);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Vendors for dropdown
  const [vendorsList, setVendorsList] = useState([]);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingExpense, setEditingExpense] = useState(null);
  const [formData, setFormData] = useState({
    category: 'Office',
    amount: '',
    expense_date: new Date().toISOString().split('T')[0],
    description: '',
    payment_method: 'BANK_TRANSFER',
    vendor_id: '',
  });
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  const categories = ['Office', 'Transport', 'Packaging', 'Electronics', 'Software', 'Marketing', 'Rent', 'Utilities', 'Other'];
  const paymentMethods = ['BANK_TRANSFER', 'UPI', 'CREDIT_CARD', 'CASH', 'CHEQUE', 'OTHER'];

  const fetchExpenses = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {
        page: 1,
        page_size: 50,
      };
      if (search.trim()) params.search = search.trim();
      if (selectedCategory) params.category = selectedCategory;
      if (selectedPaymentMethod) params.payment_method = selectedPaymentMethod;
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;

      const [resExp, resSummary] = await Promise.all([
        expenseApi.list(params),
        expenseApi.summary()
      ]);

      setExpenses(resExp.data.items || []);
      setTotalCount(resExp.data.total || 0);
      setSummary(resSummary.data || null);
    } catch (err) {
      console.error('Failed to load expenses:', err);
      setError('Unable to load expenses. Please check backend connection.');
    } finally {
      setLoading(false);
    }
  };

  const fetchVendorsDropdown = async () => {
    try {
      const res = await vendorApi.list({ page_size: 100, active_only: true });
      setVendorsList(res.data.items || []);
    } catch (err) {
      console.error('Failed to load vendors list:', err);
    }
  };

  useEffect(() => {
    fetchExpenses();
    fetchVendorsDropdown();
  }, [selectedCategory, selectedPaymentMethod, startDate, endDate]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchExpenses();
  };

  const handleOpenAddModal = () => {
    setEditingExpense(null);
    setFormData({
      category: 'Office',
      amount: '',
      expense_date: new Date().toISOString().split('T')[0],
      description: '',
      payment_method: 'BANK_TRANSFER',
      vendor_id: '',
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (expense) => {
    setEditingExpense(expense);
    setFormData({
      category: expense.category,
      amount: expense.amount,
      expense_date: expense.expense_date,
      description: expense.description,
      payment_method: expense.payment_method,
      vendor_id: expense.vendor_id || '',
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setFormError(null);
    setFormSubmitting(true);

    try {
      const payload = {
        category: formData.category,
        amount: parseFloat(formData.amount),
        expense_date: formData.expense_date,
        description: formData.description,
        payment_method: formData.payment_method,
        vendor_id: formData.vendor_id ? formData.vendor_id : null,
      };

      if (editingExpense) {
        await expenseApi.update(editingExpense.id, payload);
      } else {
        await expenseApi.create(payload);
      }

      setIsModalOpen(false);
      fetchExpenses();
    } catch (err) {
      console.error('Save expense failed:', err);
      setFormError(err.response?.data?.message || 'Failed to save expense. Please check all values.');
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleDeleteExpense = async (expense) => {
    if (!window.confirm(`Delete expense "${expense.description}" (₹${expense.amount})?`)) {
      return;
    }

    try {
      await expenseApi.delete(expense.id);
      fetchExpenses();
    } catch (err) {
      console.error('Delete expense failed:', err);
      alert(err.response?.data?.message || 'Failed to delete expense');
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Expense Management</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Log and categorize operational expenditure across departments with payment audit trails.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchExpenses}
            className="p-2 text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-sm"
            title="Refresh Expenses"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-brand-600' : ''}`} />
          </button>
          {hasRole(['ADMIN', 'STAFF']) && (
            <button
              onClick={handleOpenAddModal}
              className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-xs font-semibold shadow-sm transition-all shadow-brand-500/20"
            >
              <Plus className="w-4 h-4" />
              <span>Record Expense</span>
            </button>
          )}
        </div>
      </div>

      {/* KPI Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Total Spend Logged</span>
            <div className="text-2xl font-bold text-slate-900 mt-1">
              ₹{Number(summary?.total_expenses_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
            <span className="text-xs text-slate-500 mt-0.5 block">{summary?.total_count || 0} Total Entries</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-brand-50 border border-brand-100 flex items-center justify-center text-brand-600">
            <Receipt className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-purple-600">Top Spend Category</span>
            <div className="text-xl font-bold text-slate-900 mt-1">
              {summary?.by_category?.[0]?.category || 'None'}
            </div>
            <span className="text-xs text-purple-700 font-semibold mt-0.5 block">
              ₹{Number(summary?.by_category?.[0]?.total_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })} ({summary?.by_category?.[0]?.percentage || 0}%)
            </span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-purple-50 border border-purple-100 flex items-center justify-center text-purple-600">
            <PieChart className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-600">Primary Payment Mode</span>
            <div className="text-xl font-bold text-slate-900 mt-1">Direct Bank / UPI</div>
            <span className="text-xs text-slate-500 mt-0.5 block">Instant Settlement</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600">
            <CreditCard className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Category Breakdown Progress Bars */}
      {summary?.by_category && summary.by_category.length > 0 && (
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 mb-3">Category Distribution</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {summary.by_category.slice(0, 8).map((cat) => (
              <div key={cat.category} className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                <div className="flex justify-between items-center text-xs font-semibold">
                  <span className="text-slate-800">{cat.category}</span>
                  <span className="text-brand-700">₹{Number(cat.total_amount).toLocaleString('en-IN')}</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-1.5 mt-2 overflow-hidden">
                  <div 
                    className="bg-brand-600 h-1.5 rounded-full transition-all duration-500" 
                    style={{ width: `${Math.min(100, Math.max(5, cat.percentage))}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-[10px] text-slate-500 mt-1.5">
                  <span>{cat.count} items</span>
                  <span className="font-semibold">{cat.percentage}% of total</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters Toolbar */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3">
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search expense description..."
            className="w-full pl-9 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition"
          />
        </form>

        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>

          <select
            value={selectedPaymentMethod}
            onChange={(e) => setSelectedPaymentMethod(e.target.value)}
            className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          >
            <option value="">All Payment Modes</option>
            {paymentMethods.map((m) => (
              <option key={m} value={m}>{m.replace('_', ' ')}</option>
            ))}
          </select>

          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="px-2.5 py-1 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700"
            title="Start Date"
          />
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="px-2.5 py-1 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700"
            title="End Date"
          />
        </div>
      </div>

      {/* Expenses Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="flex flex-col items-center gap-2">
              <div className="w-8 h-8 border-2 border-brand-600 border-t-transparent rounded-full animate-spin"></div>
              <span className="text-xs text-slate-500">Loading expense ledger...</span>
            </div>
          </div>
        ) : error ? (
          <div className="p-5 text-center text-xs text-rose-600 flex items-center justify-center gap-2">
            <AlertCircle className="w-4 h-4" />
            <span>{error}</span>
          </div>
        ) : expenses.length === 0 ? (
          <div className="p-12 text-center">
            <Receipt className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <h3 className="text-sm font-bold text-slate-800">No expenses recorded</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
              Start logging your company operational expenditures for tax deductions and cashflow tracking.
            </p>
            {hasRole(['ADMIN', 'STAFF']) && (
              <button
                onClick={handleOpenAddModal}
                className="mt-4 inline-flex items-center gap-1.5 px-3.5 py-2 bg-brand-600 text-white rounded-lg text-xs font-semibold hover:bg-brand-500 transition"
              >
                <Plus className="w-4 h-4" />
                <span>Record Expense</span>
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50/75 border-b border-slate-200 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Description</th>
                  <th className="py-3 px-4">Supplier / Vendor</th>
                  <th className="py-3 px-4">Payment Mode</th>
                  <th className="py-3 px-4 text-right">Amount</th>
                  {hasRole(['ADMIN', 'STAFF']) && (
                    <th className="py-3 px-4 text-center">Actions</th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {expenses.map((expense) => (
                  <tr key={expense.id} className="hover:bg-slate-50/50 transition">
                    <td className="py-3 px-4 font-medium text-slate-700 whitespace-nowrap">
                      {expense.expense_date}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-brand-50 text-brand-700 border border-brand-100">
                        {expense.category}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-900 font-medium max-w-xs truncate">
                      {expense.description}
                    </td>
                    <td className="py-3 px-4 text-slate-600 whitespace-nowrap">
                      {expense.vendor?.name || '—'}
                    </td>
                    <td className="py-3 px-4 text-slate-600 whitespace-nowrap">
                      <span className="font-mono text-[11px] text-slate-700">
                        {expense.payment_method.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-slate-900 whitespace-nowrap">
                      ₹{Number(expense.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    {hasRole(['ADMIN', 'STAFF']) && (
                      <td className="py-3 px-4 text-center whitespace-nowrap">
                        <div className="flex items-center justify-center gap-1">
                          <button
                            onClick={() => handleOpenEditModal(expense)}
                            className="p-1.5 text-slate-400 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition"
                            title="Edit Expense"
                          >
                            <Edit className="w-3.5 h-3.5" />
                          </button>
                          {hasRole(['ADMIN']) && (
                            <button
                              onClick={() => handleDeleteExpense(expense)}
                              className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
                              title="Delete Expense"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Record / Edit Expense Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <h3 className="text-sm font-bold text-slate-900">
                {editingExpense ? 'Edit Operational Expense' : 'Record Operational Expense'}
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

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Expense Category *</label>
                  <select
                    required
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                  >
                    {categories.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Amount (₹) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    required
                    value={formData.amount}
                    onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                    placeholder="0.00"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Expense Description *</label>
                <input
                  type="text"
                  required
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="e.g. Monthly cloud server infrastructure, AWS invoice"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Expense Date *</label>
                  <input
                    type="date"
                    required
                    value={formData.expense_date}
                    onChange={(e) => setFormData({ ...formData, expense_date: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Payment Method</label>
                  <select
                    value={formData.payment_method}
                    onChange={(e) => setFormData({ ...formData, payment_method: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                  >
                    {paymentMethods.map((m) => (
                      <option key={m} value={m}>{m.replace('_', ' ')}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Linked Supplier / Vendor (Optional)</label>
                <select
                  value={formData.vendor_id}
                  onChange={(e) => setFormData({ ...formData, vendor_id: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                >
                  <option value="">-- No vendor linked --</option>
                  {vendorsList.map((v) => (
                    <option key={v.id} value={v.id}>{v.name} ({v.category})</option>
                  ))}
                </select>
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
                  {formSubmitting ? 'Saving...' : editingExpense ? 'Update Expense' : 'Record Expense'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
