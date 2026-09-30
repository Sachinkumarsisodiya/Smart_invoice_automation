import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Sparkles,
  Save,
  Loader2,
  RefreshCw,
  FileText,
  Building2,
  Calendar,
  DollarSign,
  Plus,
  Trash2,
  ExternalLink,
  ShieldCheck,
  ShieldAlert,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { invoiceService } from '../services/invoiceService';
import { StatusBadge } from '../components/common/StatusBadge';

export const InvoiceReview = () => {
  const { id } = useParams();
  const { hasRole } = useAuth();
  const navigate = useNavigate();

  const [invoice, setInvoice] = useState(null);
  const [documentBlobUrl, setDocumentBlobUrl] = useState(null);
  const [docType, setDocType] = useState('pdf');
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Editable Form State
  const [formData, setFormData] = useState({
    invoice_number: '',
    invoice_date: '',
    due_date: '',
    subtotal: '0.00',
    tax_amount: '0.00',
    total_amount: '0.00',
    currency: 'INR',
    notes: '',
  });

  const loadInvoiceData = async () => {
    setIsLoading(true);
    setError('');
    try {
      const data = await invoiceService.getInvoice(id);
      setInvoice(data);

      setFormData({
        invoice_number: data.invoice_number || '',
        invoice_date: data.invoice_date || '',
        due_date: data.due_date || '',
        subtotal: String(data.subtotal || '0.00'),
        tax_amount: String(data.tax_amount || '0.00'),
        total_amount: String(data.total_amount || '0.00'),
        currency: data.currency || 'INR',
        notes: data.notes || '',
      });

      // Load secure document blob
      try {
        const blob = await invoiceService.getDocumentBlob(id);
        const url = URL.createObjectURL(blob);
        setDocumentBlobUrl(url);
        const isPdf = blob.type.includes('pdf') || (data.document_path && data.document_path.toLowerCase().endsWith('.pdf'));
        setDocType(isPdf ? 'pdf' : (data.document_path?.split('.').pop().toLowerCase() || 'pdf'));
      } catch (docErr) {
        console.error('Failed to stream document:', docErr);
      }
    } catch (err) {
      console.error(err);
      setError('Failed to load invoice details for review.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadInvoiceData();

    return () => {
      if (documentBlobUrl) {
        URL.revokeObjectURL(documentBlobUrl);
      }
    };
  }, [id]);

  // Live Deterministic Math Validation Check
  const sub = parseFloat(formData.subtotal || 0);
  const tax = parseFloat(formData.tax_amount || 0);
  const tot = parseFloat(formData.total_amount || 0);
  const calculatedTotal = (sub + tax).toFixed(2);
  const isMathValid = Math.abs(parseFloat(calculatedTotal) - tot) <= 0.02;

  const handleInputChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleRunAiExtraction = async () => {
    setIsProcessing(true);
    setError('');
    setSuccessMessage('');
    try {
      const updated = await invoiceService.extractInvoice(id);
      setInvoice(updated);
      setFormData({
        invoice_number: updated.invoice_number || '',
        invoice_date: updated.invoice_date || '',
        due_date: updated.due_date || '',
        subtotal: String(updated.subtotal || '0.00'),
        tax_amount: String(updated.tax_amount || '0.00'),
        total_amount: String(updated.total_amount || '0.00'),
        currency: updated.currency || 'INR',
        notes: updated.notes || '',
      });
      setSuccessMessage('AI Extraction and deterministic validation completed successfully!');
    } catch (err) {
      setError(err.response?.data?.error?.message || 'AI extraction failed.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSaveChanges = async () => {
    setIsProcessing(true);
    setError('');
    setSuccessMessage('');
    try {
      const updated = await invoiceService.updateInvoice(id, {
        invoice_number: formData.invoice_number,
        invoice_date: formData.invoice_date,
        due_date: formData.due_date,
        subtotal: parseFloat(formData.subtotal || 0),
        tax_amount: parseFloat(formData.tax_amount || 0),
        total_amount: parseFloat(formData.total_amount || 0),
        currency: formData.currency,
        notes: formData.notes,
      });
      setInvoice(updated);
      setSuccessMessage('Invoice corrections saved to database.');
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to update invoice.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleApprove = async () => {
    if (!isMathValid) {
      if (!window.confirm('Math check is failing (Subtotal + Tax != Total). Are you sure you want to approve?')) {
        return;
      }
    }
    setIsProcessing(true);
    try {
      await invoiceService.approveInvoice(id);
      navigate(`/invoices/${id}`);
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to approve invoice.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReject = async () => {
    const reason = window.prompt('Please enter the reason for rejection (optional):', 'Financial mismatch or invalid vendor');
    if (reason === null) return;

    setIsProcessing(true);
    try {
      await invoiceService.rejectInvoice(id, reason);
      navigate(`/invoices/${id}`);
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to reject invoice.');
    } finally {
      setIsProcessing(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
        <p className="text-xs text-slate-500 font-medium">Loading verification workbench...</p>
      </div>
    );
  }

  const confidenceScore = parseFloat(invoice?.extraction_confidence || 85);
  const validationErrors = invoice?.validation_errors?.errors || [];

  return (
    <div className="space-y-4">
      {/* Top Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-3">
          <Link
            to={`/invoices/${id}`}
            className="p-2 rounded-lg bg-slate-50 border border-slate-200 text-slate-500 hover:text-slate-800 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-slate-900 tracking-tight flex items-center gap-2">
                <span>Invoice Review Workbench:</span>
                <span className="font-mono text-brand-600">{invoice.invoice_number}</span>
              </h2>
              <StatusBadge status={invoice.status} />
            </div>
            <p className="text-xs text-slate-500">
              Verify extracted financial data against the original uploaded document.
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        {hasRole(['ADMIN', 'STAFF']) && (
          <div className="flex items-center gap-2">
            <button
              onClick={handleRunAiExtraction}
              disabled={isProcessing}
              title="Re-run AI extraction engine"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-purple-50 border border-purple-200 text-purple-700 hover:bg-purple-100 text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4 text-purple-600" />
              <span>Re-run AI</span>
            </button>
            <button
              onClick={handleSaveChanges}
              disabled={isProcessing}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-100 border border-slate-200 text-slate-700 hover:bg-slate-200 text-xs font-semibold transition-all disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              <span>Save</span>
            </button>
            <button
              onClick={handleReject}
              disabled={isProcessing}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-rose-50 border border-rose-200 text-rose-600 hover:bg-rose-100 text-xs font-semibold transition-all disabled:opacity-50"
            >
              <XCircle className="w-4 h-4" />
              <span>Reject</span>
            </button>
            <button
              onClick={handleApprove}
              disabled={isProcessing}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md shadow-emerald-600/20 transition-all disabled:opacity-50"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>Approve Invoice</span>
            </button>
          </div>
        )}
      </div>

      {successMessage && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs rounded-xl flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
          <span>{successMessage}</span>
        </div>
      )}

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Split-Screen: Left (Document) & Right (Extraction & Form) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[750px]">
        {/* Left Pane: Original Document View (6 Cols) */}
        <div className="lg:col-span-6 bg-white rounded-2xl border border-slate-200 p-4 shadow-sm flex flex-col">
          <div className="flex items-center justify-between px-2 pb-3 border-b border-slate-100 mb-3">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <FileText className="w-4 h-4 text-brand-600" />
              <span>Original Document ({docType.toUpperCase()})</span>
            </span>
            {documentBlobUrl && (
              <a
                href={documentBlobUrl}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-brand-600 hover:text-brand-700 font-medium flex items-center gap-1"
              >
                <span>Fullscreen</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>

          <div className="flex-1 rounded-xl bg-slate-100 overflow-hidden flex items-center justify-center border border-slate-200">
            {documentBlobUrl ? (
              docType === 'pdf' ? (
                <iframe
                  src={documentBlobUrl}
                  title="Original Invoice Preview"
                  className="w-full h-full min-h-[650px] border-none"
                />
              ) : (
                <img
                  src={documentBlobUrl}
                  alt="Original Document Preview"
                  className="max-h-[650px] object-contain mx-auto"
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

        {/* Right Pane: AI Confidence & Deterministic Validation Form (6 Cols) */}
        <div className="lg:col-span-6 space-y-4 overflow-y-auto">
          {/* AI Confidence & Math Checks Card */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-purple-600" />
                <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Extraction Intelligence
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-500">AI Confidence:</span>
                <span
                  className={`text-xs font-bold px-2 py-0.5 rounded-full border ${
                    confidenceScore >= 85
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : 'bg-amber-50 text-amber-700 border-amber-200'
                  }`}
                >
                  {confidenceScore.toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Deterministic Mathematical Status Banner */}
            <div
              className={`p-3 rounded-xl border flex items-start gap-2.5 text-xs ${
                isMathValid
                  ? 'bg-emerald-50/70 border-emerald-200 text-emerald-800'
                  : 'bg-rose-50/70 border-rose-200 text-rose-800'
              }`}
            >
              {isMathValid ? (
                <ShieldCheck className="w-4 h-4 shrink-0 text-emerald-600 mt-0.5" />
              ) : (
                <ShieldAlert className="w-4 h-4 shrink-0 text-rose-600 mt-0.5" />
              )}
              <div>
                <p className="font-bold">
                  {isMathValid
                    ? 'Deterministic Mathematical Validation: PASSED'
                    : 'Deterministic Mathematical Validation: INCONSISTENT'}
                </p>
                <p className="text-[11px] mt-0.5 opacity-90">
                  Subtotal ({formData.currency} {formData.subtotal}) + Tax ({formData.currency} {formData.tax_amount}) ={' '}
                  <span className="font-semibold">{formData.currency} {calculatedTotal}</span>
                  {!isMathValid && ` (Total is recorded as ${formData.currency} ${formData.total_amount})`}
                </p>
              </div>
            </div>

            {/* Validation Errors If Any */}
            {validationErrors.length > 0 && (
              <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs space-y-1">
                <p className="font-bold flex items-center gap-1">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                  <span>Validation Warnings ({validationErrors.length})</span>
                </p>
                <ul className="list-disc pl-4 text-[11px] space-y-0.5">
                  {validationErrors.map((errStr, idx) => (
                    <li key={idx}>{errStr}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Extracted Editable Data Form */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
            <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Extracted Invoice Fields
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="block text-slate-500 font-semibold mb-1">Invoice Number</label>
                <input
                  type="text"
                  value={formData.invoice_number}
                  onChange={(e) => handleInputChange('invoice_number', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-mono font-bold focus:outline-none focus:border-brand-500"
                />
              </div>

              <div>
                <label className="block text-slate-500 font-semibold mb-1">Vendor Name</label>
                <input
                  type="text"
                  disabled
                  value={invoice.vendor?.name || 'Unassigned'}
                  className="w-full px-3 py-2 bg-slate-100 border border-slate-200 rounded-lg text-slate-600 font-semibold cursor-not-allowed"
                />
              </div>

              <div>
                <label className="block text-slate-500 font-semibold mb-1">Invoice Date</label>
                <input
                  type="date"
                  value={formData.invoice_date}
                  onChange={(e) => handleInputChange('invoice_date', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-semibold focus:outline-none focus:border-brand-500"
                />
              </div>

              <div>
                <label className="block text-slate-500 font-semibold mb-1">Due Date</label>
                <input
                  type="date"
                  value={formData.due_date}
                  onChange={(e) => handleInputChange('due_date', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-semibold focus:outline-none focus:border-brand-500"
                />
              </div>

              <div>
                <label className="block text-slate-500 font-semibold mb-1">Subtotal Amount</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.subtotal}
                  onChange={(e) => handleInputChange('subtotal', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-bold focus:outline-none focus:border-brand-500"
                />
              </div>

              <div>
                <label className="block text-slate-500 font-semibold mb-1">Tax Amount (GST/VAT)</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.tax_amount}
                  onChange={(e) => handleInputChange('tax_amount', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-bold focus:outline-none focus:border-brand-500"
                />
              </div>

              <div>
                <label className="block text-slate-500 font-semibold mb-1">Total Amount</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.total_amount}
                  onChange={(e) => handleInputChange('total_amount', e.target.value)}
                  className="w-full px-3 py-2 bg-brand-50/50 border border-brand-300 rounded-lg text-brand-700 font-bold focus:outline-none focus:border-brand-500"
                />
              </div>

              <div>
                <label className="block text-slate-500 font-semibold mb-1">Currency</label>
                <select
                  value={formData.currency}
                  onChange={(e) => handleInputChange('currency', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-semibold focus:outline-none focus:border-brand-500"
                >
                  <option value="INR">INR (₹)</option>
                  <option value="USD">USD ($)</option>
                  <option value="EUR">EUR (€)</option>
                  <option value="GBP">GBP (£)</option>
                </select>
              </div>
            </div>

            {/* Line Items Table */}
            {invoice.items && invoice.items.length > 0 && (
              <div className="mt-4 pt-4 border-t border-slate-100">
                <h4 className="text-xs font-bold text-slate-600 mb-2">Extracted Line Items</h4>
                <div className="border border-slate-200 rounded-xl overflow-hidden">
                  <table className="w-full text-left text-[11px] text-slate-600">
                    <thead className="bg-slate-50 font-bold text-slate-400 uppercase tracking-wider border-b border-slate-200">
                      <tr>
                        <th className="px-3 py-2">Item</th>
                        <th className="px-3 py-2 text-right">Qty</th>
                        <th className="px-3 py-2 text-right">Unit Price</th>
                        <th className="px-3 py-2 text-right">Amount</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {invoice.items.map((it, idx) => (
                        <tr key={idx}>
                          <td className="px-3 py-2 font-medium text-slate-800">{it.description}</td>
                          <td className="px-3 py-2 text-right">{it.quantity}</td>
                          <td className="px-3 py-2 text-right">₹{parseFloat(it.unit_price).toFixed(2)}</td>
                          <td className="px-3 py-2 text-right font-bold text-slate-900">₹{parseFloat(it.amount).toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
