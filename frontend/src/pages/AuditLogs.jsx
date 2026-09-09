import React, { useState, useEffect } from 'react';
import { ShieldCheck, Filter, Clock, Search, RefreshCw, ChevronLeft, ChevronRight, User, Globe, Activity, Eye, X } from 'lucide-react';
import { auditLogApi } from '../services/api';
import { useAuth } from '../context/AuthContext';

export const AuditLogs = () => {
  const { user } = useAuth();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [actionFilter, setActionFilter] = useState('');
  const [entityFilter, setEntityFilter] = useState('');
  const [selectedLog, setSelectedLog] = useState(null);

  const fetchAuditLogs = async () => {
    try {
      setLoading(true);
      const params = { page, page_size: 15 };
      if (actionFilter) params.action = actionFilter;
      if (entityFilter) params.entity = entityFilter;

      const res = await auditLogApi.list(params);
      setLogs(res.data.items);
      setTotal(res.data.total);
      setPages(res.data.pages);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs();
  }, [page, actionFilter, entityFilter]);

  const getActionBadgeColor = (action) => {
    if (action.includes('CREATED') || action.includes('APPROVED') || action.includes('PAID') || action.includes('REGISTER')) {
      return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    }
    if (action.includes('OVERDUE') || action.includes('REJECTED') || action.includes('DELETED') || action.includes('FAILED')) {
      return 'bg-rose-50 text-rose-700 border-rose-200';
    }
    if (action.includes('REMINDER')) {
      return 'bg-blue-50 text-blue-700 border-blue-200';
    }
    return 'bg-slate-100 text-slate-700 border-slate-200';
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2.5">
            <ShieldCheck className="w-6 h-6 text-brand-600" />
            <span>Immutable System Audit Trail</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Complete compliance record of all authentication, invoice approvals, background automation, and financial ledger events.
          </p>
        </div>

        <button
          onClick={fetchAuditLogs}
          disabled={loading}
          className="p-2.5 bg-white hover:bg-slate-50 text-slate-700 rounded-xl border border-slate-200 text-xs font-semibold flex items-center gap-1.5 shadow-sm self-start sm:self-auto"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-brand-600' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filters Toolbar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          {/* Action Filter */}
          <select
            value={actionFilter}
            onChange={(e) => {
              setActionFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          >
            <option value="">All Actions</option>
            <option value="USER_LOGIN">User Login</option>
            <option value="USER_REGISTER">User Register</option>
            <option value="INVOICE_UPLOADED">Invoice Uploaded</option>
            <option value="INVOICE_APPROVED">Invoice Approved</option>
            <option value="INVOICE_REJECTED">Invoice Rejected</option>
            <option value="INVOICE_MARKED_OVERDUE">Invoice Overdue</option>
            <option value="PAYMENT_REMINDER_SENT">Payment Reminder Sent</option>
            <option value="PAYMENT_RECORDED">Payment Recorded</option>
            <option value="VENDOR_CREATED">Vendor Created</option>
            <option value="EXPENSE_CREATED">Expense Created</option>
          </select>

          {/* Entity Filter */}
          <select
            value={entityFilter}
            onChange={(e) => {
              setEntityFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          >
            <option value="">All Entities</option>
            <option value="INVOICE">Invoice</option>
            <option value="PAYMENT">Payment</option>
            <option value="EXPENSE">Expense</option>
            <option value="VENDOR">Vendor</option>
            <option value="USER">User</option>
          </select>

          {(actionFilter || entityFilter) && (
            <button
              onClick={() => {
                setActionFilter('');
                setEntityFilter('');
                setPage(1);
              }}
              className="text-xs font-semibold text-rose-600 hover:text-rose-700 underline"
            >
              Reset Filters
            </button>
          )}
        </div>

        <span className="text-xs font-semibold text-slate-500">
          Total Logs: <strong className="text-slate-900">{total}</strong>
        </span>
      </div>

      {/* Audit Log Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider font-semibold border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Timestamp (UTC)</th>
                <th className="py-3 px-4">Action</th>
                <th className="py-3 px-4">Entity</th>
                <th className="py-3 px-4">User</th>
                <th className="py-3 px-4">IP Address</th>
                <th className="py-3 px-4 text-center">Payload</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan="6" className="py-10 text-center text-slate-400">Loading audit trail...</td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-10 text-center text-slate-400">No audit log records match the selected filters.</td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4 font-mono text-slate-600 whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold border ${getActionBadgeColor(log.action)}`}>
                        {log.action}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-semibold text-slate-800">{log.entity}</span>
                      {log.entity_id && (
                        <span className="block font-mono text-[10px] text-slate-400 truncate max-w-[120px]">
                          {log.entity_id}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-700">
                      {log.user_email || <span className="text-slate-400 italic">System / Worker</span>}
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-slate-500">
                      {log.ip_address || '—'}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {log.changes ? (
                        <button
                          onClick={() => setSelectedLog(log)}
                          className="p-1 rounded-lg text-slate-500 hover:text-brand-600 hover:bg-brand-50 transition-colors"
                          title="View Payload Details"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                      ) : (
                        <span className="text-slate-300">—</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        {pages > 1 && (
          <div className="p-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
            <span>Page {page} of {pages}</span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-1.5 rounded-lg border border-slate-200 disabled:opacity-40 hover:bg-slate-50"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage((p) => Math.min(pages, p + 1))}
                disabled={page === pages}
                className="p-1.5 rounded-lg border border-slate-200 disabled:opacity-40 hover:bg-slate-50"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Payload Inspection Modal */}
      {selectedLog && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Audit Entry Payload</h3>
                <span className="text-[11px] font-mono text-slate-400">{selectedLog.id}</span>
              </div>
              <button
                onClick={() => setSelectedLog(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500">Action:</span>
                <span className="font-bold text-slate-800">{selectedLog.action}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Timestamp:</span>
                <span className="font-mono text-slate-700">{new Date(selectedLog.timestamp).toISOString()}</span>
              </div>
            </div>

            <div className="bg-slate-900 text-emerald-400 p-4 rounded-xl font-mono text-xs overflow-x-auto max-h-60">
              <pre>{JSON.stringify(selectedLog.changes, null, 2)}</pre>
            </div>

            <button
              onClick={() => setSelectedLog(null)}
              className="w-full py-2 bg-slate-900 text-white rounded-xl text-xs font-bold hover:bg-slate-800"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
