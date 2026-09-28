import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  FileText,
  Plus,
  Search,
  Filter,
  Eye,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertCircle,
  FileCheck2,
  Mail,
  RefreshCw,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { invoiceService } from '../services/invoiceService';
import { StatusBadge } from '../components/common/StatusBadge';

export const Invoices = () => {
  const { hasRole } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const [invoices, setInvoices] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [pageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '');
  const [searchTerm, setSearchTerm] = useState(searchParams.get('search') || '');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  // Sync state if URL query changes
  useEffect(() => {
    const urlStatus = searchParams.get('status') || '';
    if (urlStatus !== statusFilter) {
      setStatusFilter(urlStatus);
    }
  }, [searchParams]);

  const [isSyncingEmail, setIsSyncingEmail] = useState(false);
  const [syncMessage, setSyncMessage] = useState('');

  const fetchInvoices = async () => {
    setIsLoading(true);
    setError('');
    try {
      const data = await invoiceService.getInvoices({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
        search: searchTerm || undefined,
      });
      setInvoices(data.items);
      setTotal(data.total);
      setPages(data.pages);
    } catch (err) {
      console.error('Failed to load invoices:', err);
      setError('Failed to fetch invoice list from server.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSyncEmail = async () => {
    setIsSyncingEmail(true);
    setSyncMessage('');
    setError('');
    try {
      const res = await invoiceService.fetchFromEmail();
      if (res.success) {
        setSyncMessage(`✅ ${res.message || 'Email sync completed successfully.'}`);
        fetchInvoices();
      } else {
        setError(`⚠️ ${res.message || 'Failed to sync from email.'}`);
      }
    } catch (err) {
      setError(err.response?.data?.message || err.response?.data?.error?.message || 'Error connecting to email service.');
    } finally {
      setIsSyncingEmail(false);
    }
  };

  useEffect(() => {
    fetchInvoices();
  }, [page, statusFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchInvoices();
  };

  const handleDelete = async (id, invoiceNumber) => {
    if (!window.confirm(`Are you sure you want to delete invoice ${invoiceNumber}?`)) {
      return;
    }
    try {
      await invoiceService.deleteInvoice(id);
      fetchInvoices();
    } catch (err) {
      alert(err.response?.data?.error?.message || 'Failed to delete invoice.');
    }
  };

  const formatCurrency = (val, currency = 'INR') => {
    const symbol = currency === 'INR' ? '₹' : '$';
    return `${symbol}${parseFloat(val || 0).toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Invoices</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Total {total} invoices recorded across all supplier accounts.
          </p>
        </div>
        {hasRole(['ADMIN', 'STAFF']) && (
          <div className="flex items-center gap-2">
            <button
              onClick={handleSyncEmail}
              disabled={isSyncingEmail}
              className="inline-flex items-center gap-2 px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 rounded-lg text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
              title="Fetch unread invoice attachments from sachinsisodiyaofc@gmail.com"
            >
              {isSyncingEmail ? (
                <Loader2 className="w-4 h-4 animate-spin text-brand-600" />
              ) : (
                <Mail className="w-4 h-4 text-brand-600" />
              )}
              <span>{isSyncingEmail ? 'Syncing Gmail...' : 'Sync from Gmail'}</span>
            </button>
            <Link
              to="/invoices/upload"
              className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-xs font-semibold shadow-sm transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>Upload Invoice</span>
            </Link>
          </div>
        )}
      </div>

      {syncMessage && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileCheck2 className="w-4 h-4 shrink-0 text-emerald-600" />
            <span>{syncMessage}</span>
          </div>
          <button
            onClick={() => setSyncMessage('')}
            className="text-emerald-600 hover:text-emerald-900 font-bold px-1"
          >
            ×
          </button>
        </div>
      )}

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => setError('')}
            className="text-rose-600 hover:text-rose-900 font-bold px-1"
          >
            ×
          </button>
        </div>
      )}

      {/* Filter / Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3">
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search invoice #, vendor..."
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:border-brand-500"
          />
        </form>
        <div className="flex items-center gap-2 w-full md:w-auto">
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-700 focus:outline-none focus:border-brand-500"
          >
            <option value="">All Statuses</option>
            <option value="PROCESSING">Processing</option>
            <option value="PENDING_REVIEW">Pending Review</option>
            <option value="APPROVED">Approved</option>
            <option value="PAID">Paid</option>
            <option value="OVERDUE">Overdue</option>
          </select>
        </div>
      </div>

      {/* Invoices Table Container */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center flex flex-col items-center justify-center gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-brand-600" />
            <p className="text-xs text-slate-400 font-medium">Loading invoices...</p>
          </div>
        ) : invoices.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-12 h-12 bg-slate-50 text-slate-400 rounded-xl flex items-center justify-center mx-auto mb-3">
              <FileText className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-slate-800">No Invoices Found</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-4">
              {searchTerm || statusFilter
                ? 'No invoices match your current search or filter criteria.'
                : 'Upload your first invoice PDF or image to begin document extraction.'}
            </p>
            {hasRole(['ADMIN', 'STAFF']) && !searchTerm && !statusFilter && (
              <Link
                to="/invoices/upload"
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-brand-600 text-white rounded-lg text-xs font-semibold hover:bg-brand-500 transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Upload Invoice</span>
              </Link>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-200">
                <tr>
                  <th className="px-5 py-3">Invoice #</th>
                  <th className="px-5 py-3">Vendor</th>
                  <th className="px-5 py-3">Date</th>
                  <th className="px-5 py-3">Due Date</th>
                  <th className="px-5 py-3 text-right">Total Amount</th>
                  <th className="px-5 py-3 text-center">Status</th>
                  <th className="px-5 py-3 text-center">Payment</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {invoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-5 py-3.5 font-bold text-slate-900 font-mono">
                      <Link to={`/invoices/${inv.id}`} className="hover:text-brand-600 hover:underline">
                        {inv.invoice_number}
                      </Link>
                    </td>
                    <td className="px-5 py-3.5 font-semibold text-slate-800">
                      {inv.vendor?.name || 'Unassigned'}
                    </td>
                    <td className="px-5 py-3.5 text-slate-500">{inv.invoice_date}</td>
                    <td className="px-5 py-3.5 text-slate-500">{inv.due_date}</td>
                    <td className="px-5 py-3.5 text-right font-bold text-slate-900">
                      {parseFloat(inv.total_amount || 0) <= 0 ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-600 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                          ⚠️ Needs Review (₹0.00)
                        </span>
                      ) : (
                        formatCurrency(inv.total_amount, inv.currency)
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-center">
                      {inv.extraction_status === 'FAILED' ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-700">
                          NEEDS VERIFICATION
                        </span>
                      ) : (
                        <StatusBadge status={inv.status} />
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-center">
                      <StatusBadge status={inv.payment_status} />
                    </td>
                    <td className="px-5 py-3.5 text-right space-x-1">
                      <Link
                        to={`/invoices/${inv.id}`}
                        title="View Details"
                        className="inline-flex p-1.5 text-slate-400 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition-colors"
                      >
                        <Eye className="w-4 h-4" />
                      </Link>
                      {hasRole('ADMIN') && (
                        <button
                          onClick={() => handleDelete(inv.id, inv.invoice_number)}
                          title="Delete Invoice"
                          className="inline-flex p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {pages > 1 && (
          <div className="px-5 py-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500 bg-slate-50/50">
            <span>
              Showing Page <span className="font-semibold text-slate-700">{page}</span> of{' '}
              <span className="font-semibold text-slate-700">{pages}</span>
            </span>
            <div className="flex items-center gap-1">
              <button
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="p-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 disabled:opacity-40 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                disabled={page >= pages}
                onClick={() => setPage(page + 1)}
                className="p-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 disabled:opacity-40 transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
