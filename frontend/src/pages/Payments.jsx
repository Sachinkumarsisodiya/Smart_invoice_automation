import React, { useState, useEffect } from 'react';
import { 
  CreditCard, Plus, ArrowDownRight, Search, Calendar, 
  CheckCircle2, AlertCircle, RefreshCw, IndianRupee, 
  Building2, FileText, ExternalLink, X, ArrowUpRight
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { paymentApi } from '../services/api';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

export const Payments = () => {
  const { hasRole } = useAuth();
  const [payments, setPayments] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [search, setSearch] = useState('');
  const [selectedMethod, setSelectedMethod] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Unpaid Invoices for modal
  const [unpaidInvoices, setUnpaidInvoices] = useState([]);
  const [selectedInvoice, setSelectedInvoice] = useState(null);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    invoice_id: '',
    amount: '',
    payment_date: new Date().toISOString().split('T')[0],
    payment_method: 'BANK_TRANSFER',
    reference_number: '',
    notes: '',
  });
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  const paymentMethods = ['BANK_TRANSFER', 'UPI', 'CREDIT_CARD', 'CASH', 'CHEQUE', 'OTHER'];

  const fetchPayments = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {
        page: 1,
        page_size: 50,
      };
      if (search.trim()) params.search = search.trim();
      if (selectedMethod) params.payment_method = selectedMethod;
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;

      const res = await paymentApi.list(params);
      setPayments(res.data.items || []);
      setTotalCount(res.data.total || 0);
    } catch (err) {
      console.error('Failed to load payments:', err);
      setError('Unable to load payment ledger. Please check backend connection.');
    } finally {
      setLoading(false);
    }
  };

  const fetchUnpaidInvoices = async () => {
    try {
      // Fetch invoices with remaining balance > 0
      const res = await api.get('/invoices', { params: { page_size: 100 } });
      const items = res.data.items || [];
      // Filter to invoices that are APPROVED or PARTIALLY_PAID and have remaining balance > 0
      const payable = items.filter(
        (inv) => (inv.status === 'APPROVED' || inv.payment_status === 'PARTIALLY_PAID') && 
                 parseFloat(inv.remaining_amount) > 0
      );
      setUnpaidInvoices(payable);
    } catch (err) {
      console.error('Failed to fetch unpaid invoices:', err);
    }
  };

  useEffect(() => {
    fetchPayments();
    fetchUnpaidInvoices();
  }, [selectedMethod, startDate, endDate]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchPayments();
  };

  const handleOpenRecordModal = (invoiceToPreselect = null) => {
    fetchUnpaidInvoices();
    setSelectedInvoice(invoiceToPreselect);
    setFormData({
      invoice_id: invoiceToPreselect ? invoiceToPreselect.id : '',
      amount: invoiceToPreselect ? invoiceToPreselect.remaining_amount : '',
      payment_date: new Date().toISOString().split('T')[0],
      payment_method: 'BANK_TRANSFER',
      reference_number: '',
      notes: '',
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleInvoiceChange = (e) => {
    const invId = e.target.value;
    const found = unpaidInvoices.find((inv) => inv.id === invId);
    setSelectedInvoice(found || null);
    setFormData({
      ...formData,
      invoice_id: invId,
      amount: found ? found.remaining_amount : '',
    });
  };

  const handleFillFullRemaining = () => {
    if (selectedInvoice) {
      setFormData({ ...formData, amount: selectedInvoice.remaining_amount });
    }
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setFormError(null);
    setFormSubmitting(true);

    try {
      const payload = {
        invoice_id: formData.invoice_id,
        amount: parseFloat(formData.amount),
        payment_date: formData.payment_date,
        payment_method: formData.payment_method,
        reference_number: formData.reference_number || null,
        notes: formData.notes || null,
      };

      await paymentApi.record(payload);
      setIsModalOpen(false);
      fetchPayments();
      fetchUnpaidInvoices();
    } catch (err) {
      console.error('Record payment failed:', err);
      setFormError(err.response?.data?.message || 'Failed to record payment transaction.');
    } finally {
      setFormSubmitting(false);
    }
  };

  const totalSettledAmount = payments.reduce((acc, p) => acc + parseFloat(p.amount || 0), 0);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Payments & Settlement Ledger</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Full and partial settlement transaction ledger with atomic balance and status synchronization.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchPayments}
            className="p-2 text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-sm"
            title="Refresh Ledger"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-brand-600' : ''}`} />
          </button>
          {hasRole(['ADMIN', 'STAFF']) && (
            <button
              onClick={() => handleOpenRecordModal()}
              className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-xs font-semibold shadow-sm transition-all shadow-brand-500/20"
            >
              <Plus className="w-4 h-4" />
              <span>Record Payment</span>
            </button>
          )}
        </div>
      </div>

      {/* KPI Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-600">Total Settled Value</span>
            <div className="text-2xl font-bold text-slate-900 mt-1">
              ₹{totalSettledAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
            <span className="text-xs text-slate-500 mt-0.5 block">{totalCount} Payment Transaction(s)</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600">
            <CheckCircle2 className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-600">Pending Invoices to Settle</span>
            <div className="text-2xl font-bold text-amber-700 mt-1">
              {unpaidInvoices.length}
            </div>
            <span className="text-xs text-slate-500 mt-0.5 block">Approved & Unpaid</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-amber-50 border border-amber-100 flex items-center justify-center text-amber-600">
            <FileText className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-brand-600">Average Settlement</span>
            <div className="text-2xl font-bold text-slate-900 mt-1">
              ₹{(totalCount > 0 ? totalSettledAmount / totalCount : 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <span className="text-xs text-slate-500 mt-0.5 block">Per Transaction</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-brand-50 border border-brand-100 flex items-center justify-center text-brand-600">
            <CreditCard className="w-6 h-6" />
          </div>
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
            placeholder="Search invoice #, vendor, reference..."
            className="w-full pl-9 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition"
          />
        </form>

        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          <select
            value={selectedMethod}
            onChange={(e) => setSelectedMethod(e.target.value)}
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

      {/* Payment Transactions Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="flex flex-col items-center gap-2">
              <div className="w-8 h-8 border-2 border-brand-600 border-t-transparent rounded-full animate-spin"></div>
              <span className="text-xs text-slate-500">Loading payment ledger...</span>
            </div>
          </div>
        ) : error ? (
          <div className="p-5 text-center text-xs text-rose-600 flex items-center justify-center gap-2">
            <AlertCircle className="w-4 h-4" />
            <span>{error}</span>
          </div>
        ) : payments.length === 0 ? (
          <div className="p-12 text-center">
            <CreditCard className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <h3 className="text-sm font-bold text-slate-800">No payment transactions recorded</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
              Record payments against approved invoices to update remaining balances in real time.
            </p>
            {hasRole(['ADMIN', 'STAFF']) && unpaidInvoices.length > 0 && (
              <button
                onClick={() => handleOpenRecordModal()}
                className="mt-4 inline-flex items-center gap-1.5 px-3.5 py-2 bg-brand-600 text-white rounded-lg text-xs font-semibold hover:bg-brand-500 transition"
              >
                <Plus className="w-4 h-4" />
                <span>Record First Payment</span>
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50/75 border-b border-slate-200 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  <th className="py-3 px-4">Payment Date</th>
                  <th className="py-3 px-4">Invoice #</th>
                  <th className="py-3 px-4">Vendor / Payee</th>
                  <th className="py-3 px-4">Payment Mode</th>
                  <th className="py-3 px-4">Reference / UTR #</th>
                  <th className="py-3 px-4">Status Result</th>
                  <th className="py-3 px-4 text-right">Amount Settled</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {payments.map((payment) => (
                  <tr key={payment.id} className="hover:bg-slate-50/50 transition">
                    <td className="py-3 px-4 font-medium text-slate-700 whitespace-nowrap">
                      {payment.payment_date}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <Link
                        to={`/invoices/${payment.invoice_id}`}
                        className="inline-flex items-center gap-1 font-mono font-bold text-brand-600 hover:text-brand-700 hover:underline"
                      >
                        <span>{payment.invoice_number || 'View Invoice'}</span>
                        <ExternalLink className="w-3 h-3" />
                      </Link>
                    </td>
                    <td className="py-3 px-4 text-slate-900 font-medium whitespace-nowrap">
                      {payment.vendor_name || '—'}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className="font-mono text-[11px] text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                        {payment.payment_method.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-600 whitespace-nowrap">
                      {payment.reference_number || '—'}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      {payment.invoice_payment_status === 'PAID' ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-100">
                          <CheckCircle2 className="w-3 h-3" /> Fully Settled
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-100">
                          <ArrowDownRight className="w-3 h-3" /> Partially Paid
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-slate-900 whitespace-nowrap">
                      ₹{Number(payment.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Record Payment Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
                  <CreditCard className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Record Settlement Payment</h3>
                  <p className="text-[11px] text-slate-500">Atomic ledger entry & invoice balance update</p>
                </div>
              </div>
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
                <label className="block text-xs font-semibold text-slate-700 mb-1">Select Invoice to Settle *</label>
                <select
                  required
                  value={formData.invoice_id}
                  onChange={handleInvoiceChange}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                >
                  <option value="">-- Choose an approved invoice --</option>
                  {unpaidInvoices.map((inv) => (
                    <option key={inv.id} value={inv.id}>
                      #{inv.invoice_number} - {inv.vendor?.name || 'Vendor'} (Remaining: ₹{Number(inv.remaining_amount).toLocaleString('en-IN')})
                    </option>
                  ))}
                </select>
              </div>

              {selectedInvoice && (
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1.5">
                  <div className="flex justify-between text-slate-600">
                    <span>Invoice Total:</span>
                    <span className="font-semibold text-slate-900">₹{Number(selectedInvoice.total_amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                  </div>
                  <div className="flex justify-between text-slate-600">
                    <span>Already Settled:</span>
                    <span className="text-emerald-700 font-semibold">₹{Number(selectedInvoice.paid_amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                  </div>
                  <div className="flex justify-between items-center pt-1 border-t border-slate-200 font-bold text-amber-800">
                    <span>Remaining Balance:</span>
                    <span>₹{Number(selectedInvoice.remaining_amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                  </div>
                </div>
              )}

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-xs font-semibold text-slate-700">Payment Amount (₹) *</label>
                  {selectedInvoice && (
                    <button
                      type="button"
                      onClick={handleFillFullRemaining}
                      className="text-[11px] font-semibold text-brand-600 hover:text-brand-700 underline"
                    >
                      Pay Full Remaining
                    </button>
                  )}
                </div>
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

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Payment Date *</label>
                  <input
                    type="date"
                    required
                    value={formData.payment_date}
                    onChange={(e) => setFormData({ ...formData, payment_date: e.target.value })}
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
                <label className="block text-xs font-semibold text-slate-700 mb-1">Transaction Ref / UTR / Cheque #</label>
                <input
                  type="text"
                  value={formData.reference_number}
                  onChange={(e) => setFormData({ ...formData, reference_number: e.target.value })}
                  placeholder="e.g. UTR-98234710923 / CHQ-1049"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Payment Notes (Optional)</label>
                <input
                  type="text"
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="e.g. Paid via ICICI Corporate Banking"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                />
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
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg transition shadow-sm disabled:opacity-50"
                >
                  {formSubmitting ? 'Recording...' : 'Record Payment Settlement'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
