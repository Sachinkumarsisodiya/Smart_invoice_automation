import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Calendar,
  Building2,
  FileText,
  DollarSign,
  Download,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  FileCode2,
  ExternalLink,
  FileCheck2,
  CreditCard,
  X,
  AlertCircle,
  ArrowDownRight,
  Mail,
  Send,
  Plus
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { invoiceService } from '../services/invoiceService';
import { paymentApi, invoiceApi } from '../services/api';
import { StatusBadge } from '../components/common/StatusBadge';

export const InvoiceDetail = () => {
  const { id } = useParams();
  const { hasRole } = useAuth();
  const navigate = useNavigate();

  const [invoice, setInvoice] = useState(null);
  const [payments, setPayments] = useState([]);
  const [documentBlobUrl, setDocumentBlobUrl] = useState(null);
  const [docType, setDocType] = useState('pdf');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  // Record Payment Modal
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
  const [paymentAmount, setPaymentAmount] = useState('');
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().split('T')[0]);
  const [paymentMethod, setPaymentMethod] = useState('BANK_TRANSFER');
  const [referenceNumber, setReferenceNumber] = useState('');
  const [paymentNotes, setPaymentNotes] = useState('');
  const [paymentSubmitting, setPaymentSubmitting] = useState(false);
  const [paymentError, setPaymentError] = useState(null);

  // Manual Reminder Trigger State
  const [sendingReminder, setSendingReminder] = useState(false);
  const [reminderMsg, setReminderMsg] = useState(null);

  const handleSendReminder = async () => {
    try {
      setSendingReminder(true);
      setReminderMsg(null);
      await invoiceApi.sendReminder(id);
      setReminderMsg({ type: 'success', text: 'Payment reminder dispatched successfully!' });
      setTimeout(() => setReminderMsg(null), 5000);
    } catch (err) {
      console.error('Failed to dispatch payment reminder:', err);
      setReminderMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to dispatch payment reminder.' });
      setTimeout(() => setReminderMsg(null), 5000);
    } finally {
      setSendingReminder(false);
    }
  };

  const loadInvoiceAndDoc = async () => {
    setIsLoading(true);
    setError('');
    try {
      const invData = await invoiceService.getInvoice(id);
      setInvoice(invData);

      // Fetch payments for this invoice
      try {
        const payRes = await paymentApi.list({ invoice_id: id });
        setPayments(payRes.data.items || []);
      } catch (pErr) {
        console.error('Failed to load payment history:', pErr);
      }

      // Fetch document blob securely
      try {
        const blob = await invoiceService.getDocumentBlob(id);
        const url = URL.createObjectURL(blob);
        setDocumentBlobUrl(url);

        const isPdf = blob.type.includes('pdf') || (invData.document_path && invData.document_path.toLowerCase().endsWith('.pdf'));
        setDocType(isPdf ? 'pdf' : (invData.document_path?.split('.').pop().toLowerCase() || 'pdf'));
      } catch (docErr) {
        console.error('Failed to load document stream:', docErr);
      }
    } catch (err) {
      console.error(err);
      setError('Failed to load invoice details.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadInvoiceAndDoc();

    return () => {
      if (documentBlobUrl) {
        URL.revokeObjectURL(documentBlobUrl);
      }
    };
  }, [id]);

  const handleDelete = async () => {
    if (!window.confirm(`Are you sure you want to delete invoice ${invoice.invoice_number}?`)) {
      return;
    }
    try {
      await invoiceService.deleteInvoice(id);
      navigate('/invoices');
    } catch (err) {
      alert(err.response?.data?.error?.message || 'Failed to delete invoice.');
    }
  };

  const handleOpenPaymentModal = () => {
    setPaymentAmount(invoice.remaining_amount || '0.00');
    setPaymentDate(new Date().toISOString().split('T')[0]);
    setPaymentMethod('BANK_TRANSFER');
    setReferenceNumber('');
    setPaymentNotes('');
    setPaymentError(null);
    setIsPaymentModalOpen(true);
  };

  const handleRecordPaymentSubmit = async (e) => {
    e.preventDefault();
    setPaymentError(null);
    setPaymentSubmitting(true);

    try {
      await paymentApi.record({
        invoice_id: invoice.id,
        amount: parseFloat(paymentAmount),
        payment_date: paymentDate,
        payment_method: paymentMethod,
        reference_number: referenceNumber || null,
        notes: paymentNotes || null,
      });

      setIsPaymentModalOpen(false);
      loadInvoiceAndDoc();
    } catch (err) {
      console.error('Payment failed:', err);
      setPaymentError(err.response?.data?.message || 'Failed to record payment.');
    } finally {
      setPaymentSubmitting(false);
    }
  };

  const formatCurrency = (val, currency = 'INR') => {
    const symbol = currency === 'INR' ? '₹' : '$';
    return `${symbol}${parseFloat(val || 0).toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  if (isLoading) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
        <p className="text-xs text-slate-500 font-medium">Loading invoice details & document...</p>
      </div>
    );
  }

  if (error || !invoice) {
    return (
      <div className="p-8 text-center bg-white rounded-2xl border border-slate-200">
        <AlertTriangle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
        <h3 className="text-sm font-bold text-slate-800">Invoice Not Found</h3>
        <p className="text-xs text-slate-500 mt-1 mb-4">{error || 'Unable to retrieve invoice record.'}</p>
        <Link
          to="/invoices"
          className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-xs font-semibold"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Invoices</span>
        </Link>
      </div>
    );
  }

  const remainingNum = parseFloat(invoice.remaining_amount || 0);

  return (
    <div className="space-y-6">
      {/* Top Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            to="/invoices"
            className="p-2 rounded-lg bg-white border border-slate-200 text-slate-500 hover:text-slate-800 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2.5">
              <h2 className="text-xl font-bold text-slate-900 font-mono tracking-tight">
                {invoice.invoice_number}
              </h2>
              <StatusBadge status={invoice.status} />
              <StatusBadge status={invoice.payment_status} />
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Issued by <span className="font-semibold text-slate-700">{invoice.vendor?.name}</span> on {invoice.invoice_date}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {hasRole(['ADMIN', 'STAFF']) && remainingNum > 0 && (
            <button
              onClick={handleOpenPaymentModal}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-sm transition-colors shadow-emerald-600/20"
            >
              <CreditCard className="w-4 h-4" />
              <span>Record Payment</span>
            </button>
          )}
          {hasRole(['ADMIN', 'STAFF']) && remainingNum > 0 && (
            <button
              onClick={handleSendReminder}
              disabled={sendingReminder}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-sm transition-colors"
              title="Dispatch payment reminder email to supplier"
            >
              <Mail className={`w-4 h-4 ${sendingReminder ? 'animate-spin' : ''}`} />
              <span>{sendingReminder ? 'Sending...' : 'Send Reminder'}</span>
            </button>
          )}
          {hasRole(['ADMIN', 'STAFF']) && (
            <Link
              to={`/invoices/${invoice.id}/review`}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-sm transition-colors"
            >
              <FileCheck2 className="w-4 h-4" />
              <span>Review & Verify</span>
            </Link>
          )}
          {documentBlobUrl && (
            <a
              href={documentBlobUrl}
              download={`invoice_${invoice.invoice_number}.${docType}`}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-semibold shadow-sm transition-colors"
            >
              <Download className="w-4 h-4" />
              <span>Download File</span>
            </a>
          )}
          {hasRole('ADMIN') && (
            <button
              onClick={handleDelete}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-rose-50 border border-rose-200 text-rose-600 hover:bg-rose-100 text-xs font-semibold transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              <span>Delete</span>
            </button>
          )}
        </div>
      </div>

      {reminderMsg && (
        <div
          className={`p-4 rounded-xl text-xs font-semibold flex items-center gap-2 animate-in fade-in duration-150 ${
            reminderMsg.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              : 'bg-rose-50 text-rose-800 border border-rose-200'
          }`}
        >
          {reminderMsg.type === 'success' ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <AlertCircle className="w-4 h-4 text-rose-600" />}
          <span>{reminderMsg.text}</span>
        </div>
      )}

      {/* Split View: Financial Metadata (Left) & Document Preview (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Details, Items & Payments (5 Cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Summary Card */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                Financial Breakdown
              </h3>
              {remainingNum > 0 && hasRole(['ADMIN', 'STAFF']) && (
                <button
                  onClick={handleOpenPaymentModal}
                  className="text-xs font-semibold text-emerald-600 hover:text-emerald-700 flex items-center gap-1"
                >
                  <Plus className="w-3.5 h-3.5" /> Settle Balance
                </button>
              )}
            </div>
            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-100 text-slate-600">
                <span>Subtotal:</span>
                <span className="font-semibold text-slate-800">{formatCurrency(invoice.subtotal, invoice.currency)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100 text-slate-600">
                <span>Tax Amount:</span>
                <span className="font-semibold text-slate-800">{formatCurrency(invoice.tax_amount, invoice.currency)}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-slate-200 text-sm font-bold text-slate-900">
                <span>Total Amount:</span>
                <span className="text-brand-600">{formatCurrency(invoice.total_amount, invoice.currency)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100 text-slate-600">
                <span>Paid Amount:</span>
                <span className="font-semibold text-emerald-600">{formatCurrency(invoice.paid_amount, invoice.currency)}</span>
              </div>
              <div className="flex justify-between py-1 text-slate-600">
                <span>Remaining Balance:</span>
                <span className={`font-bold ${remainingNum > 0 ? 'text-amber-600' : 'text-slate-500'}`}>
                  {formatCurrency(invoice.remaining_amount, invoice.currency)}
                </span>
              </div>
            </div>
          </div>

          {/* Payment History Card */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-3">
            <div className="flex justify-between items-center">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <CreditCard className="w-4 h-4 text-emerald-600" />
                <span>Payment Settlement History</span>
              </h3>
              <span className="text-[11px] font-semibold text-slate-500">{payments.length} record(s)</span>
            </div>

            {payments.length === 0 ? (
              <div className="text-center py-4 bg-slate-50 rounded-xl border border-slate-100 text-xs text-slate-500">
                No payments have been recorded for this invoice yet.
              </div>
            ) : (
              <div className="space-y-2">
                {payments.map((p) => (
                  <div key={p.id} className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs flex items-center justify-between">
                    <div>
                      <div className="font-bold text-slate-900">
                        ₹{Number(p.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        {p.payment_date} &bull; <span className="font-mono">{p.payment_method.replace('_', ' ')}</span>
                      </div>
                      {p.reference_number && (
                        <div className="text-[10px] text-slate-400 font-mono">Ref: {p.reference_number}</div>
                      )}
                    </div>
                    <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full text-[10px] font-semibold border border-emerald-100">
                      Settled
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Vendor Details Card */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-3">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Building2 className="w-4 h-4 text-slate-500" />
              <span>Vendor Information</span>
            </h3>
            <div className="text-xs space-y-1.5 text-slate-600">
              <p className="font-bold text-sm text-slate-900">{invoice.vendor?.name}</p>
              <p>Email: <span className="text-slate-800">{invoice.vendor?.email || 'N/A'}</span></p>
              <p>GSTIN: <span className="font-mono text-slate-800">{invoice.vendor?.gstin || 'N/A'}</span></p>
              <p>Category: <span className="font-semibold text-brand-600">{invoice.vendor?.category}</span></p>
              <p>Due Date: <span className="font-semibold text-slate-800">{invoice.due_date}</span></p>
            </div>
          </div>
        </div>

        {/* Right Column: Embedded Secure Document Preview (7 Cols) */}
        <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200 p-4 shadow-sm flex flex-col min-h-[650px]">
          <div className="flex items-center justify-between px-2 pb-3 border-b border-slate-100 mb-3">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <FileText className="w-4 h-4 text-brand-600" />
              <span>Secure Document Viewer ({docType.toUpperCase()})</span>
            </span>
            {documentBlobUrl && (
              <a
                href={documentBlobUrl}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-brand-600 hover:text-brand-700 font-medium flex items-center gap-1"
              >
                <span>Open in Tab</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>

          <div className="flex-1 rounded-xl bg-slate-100 overflow-hidden flex items-center justify-center border border-slate-200">
            {documentBlobUrl ? (
              docType === 'pdf' ? (
                <iframe
                  src={documentBlobUrl}
                  title="Invoice PDF Preview"
                  className="w-full h-full min-h-[600px] border-none"
                />
              ) : (
                <img
                  src={documentBlobUrl}
                  alt="Invoice Document Preview"
                  className="max-h-[600px] object-contain mx-auto"
                />
              )
            ) : (
              <div className="text-center p-8 text-slate-400">
                <FileText className="w-10 h-10 mx-auto mb-2 text-slate-300" />
                <p className="text-xs">Document stream unavailable.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Record Payment Modal */}
      {isPaymentModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
                  <CreditCard className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Record Payment</h3>
                  <p className="text-[11px] text-slate-500">Invoice #{invoice.invoice_number}</p>
                </div>
              </div>
              <button
                onClick={() => setIsPaymentModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleRecordPaymentSubmit} className="p-5 space-y-4">
              {paymentError && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{paymentError}</span>
                </div>
              )}

              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1.5">
                <div className="flex justify-between text-slate-600">
                  <span>Invoice Total:</span>
                  <span className="font-semibold text-slate-900">{formatCurrency(invoice.total_amount, invoice.currency)}</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Already Settled:</span>
                  <span className="text-emerald-700 font-semibold">{formatCurrency(invoice.paid_amount, invoice.currency)}</span>
                </div>
                <div className="flex justify-between items-center pt-1 border-t border-slate-200 font-bold text-amber-800">
                  <span>Remaining Unpaid:</span>
                  <span>{formatCurrency(invoice.remaining_amount, invoice.currency)}</span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Payment Amount (₹) *</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max={parseFloat(invoice.remaining_amount || 0)}
                  required
                  value={paymentAmount}
                  onChange={(e) => setPaymentAmount(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Payment Date *</label>
                  <input
                    type="date"
                    required
                    value={paymentDate}
                    onChange={(e) => setPaymentDate(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Payment Method</label>
                  <select
                    value={paymentMethod}
                    onChange={(e) => setPaymentMethod(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                  >
                    <option value="BANK_TRANSFER">Bank Transfer</option>
                    <option value="UPI">UPI</option>
                    <option value="CREDIT_CARD">Credit Card</option>
                    <option value="CASH">Cash</option>
                    <option value="CHEQUE">Cheque</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Reference / UTR / Cheque #</label>
                <input
                  type="text"
                  value={referenceNumber}
                  onChange={(e) => setReferenceNumber(e.target.value)}
                  placeholder="e.g. UTR-98234710923 / CHQ-1049"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Notes (Optional)</label>
                <input
                  type="text"
                  value={paymentNotes}
                  onChange={(e) => setPaymentNotes(e.target.value)}
                  placeholder="e.g. Cleared via primary current account"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsPaymentModalOpen(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={paymentSubmitting}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg transition shadow-sm disabled:opacity-50"
                >
                  {paymentSubmitting ? 'Recording...' : 'Settle Payment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
