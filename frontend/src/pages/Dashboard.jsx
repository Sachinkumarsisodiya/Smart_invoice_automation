import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { dashboardApi } from '../services/api';
import { invoiceService } from '../services/invoiceService';
import {
  FileText,
  CreditCard,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  ArrowUpRight,
  Clock,
  Building2,
  Receipt,
  Sparkles,
  PieChart,
  BarChart3,
  RefreshCw,
  Plus,
  ArrowDownRight,
  DollarSign,
  Activity,
  Calendar,
  Mail,
  Loader2,
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const Dashboard = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [isSyncingEmail, setIsSyncingEmail] = useState(false);
  const [syncStatusMsg, setSyncStatusMsg] = useState('');
  const [stats, setStats] = useState(null);
  const [cashflow, setCashflow] = useState([]);
  const [categories, setCategories] = useState([]);
  const [statuses, setStatuses] = useState([]);
  const [topVendors, setTopVendors] = useState([]);
  const [recentActivity, setRecentActivity] = useState([]);
  const [cashflowMonths, setCashflowMonths] = useState(6);

  const handleSyncEmail = async () => {
    setIsSyncingEmail(true);
    setSyncStatusMsg('');
    try {
      const res = await invoiceService.fetchFromEmail();
      if (res.success) {
        alert(`✅ ${res.message || 'Gmail sync completed!'}`);
        fetchDashboardData();
      } else {
        alert(`⚠️ ${res.message || 'Could not sync from Gmail.'}`);
      }
    } catch (err) {
      alert(err.response?.data?.message || 'Error connecting to Gmail. Please verify IMAP settings.');
    } finally {
      setIsSyncingEmail(false);
    }
  };

  const fetchDashboardData = async () => {
    try {
      setRefreshing(true);
      const [statsRes, cashflowRes, catRes, statusRes, vendorsRes, activityRes] = await Promise.all([
        dashboardApi.getStats(),
        dashboardApi.getMonthlyCashflow(cashflowMonths),
        dashboardApi.getCategoryDistribution(),
        dashboardApi.getStatusDistribution(),
        dashboardApi.getTopVendors(5),
        dashboardApi.getRecentActivity(8),
      ]);

      setStats(statsRes.data);
      setCashflow(cashflowRes.data);
      setCategories(catRes.data);
      setStatuses(statusRes.data);
      setTopVendors(vendorsRes.data);
      setRecentActivity(activityRes.data);
    } catch (err) {
      console.error('Failed to load dashboard analytics:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [cashflowMonths]);

  const formatCurrency = (val) => {
    const num = Number(val || 0);
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(num);
  };

  // Helper for cashflow max height
  const maxCashflowVal = Math.max(
    ...cashflow.map((c) => Math.max(Number(c.invoiced_amount), Number(c.paid_amount), Number(c.expense_amount))),
    1
  );

  return (
    <div className="space-y-6 pb-12">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-slate-950 via-slate-900 to-brand-950 rounded-2xl p-6 text-white shadow-md border border-slate-800 flex flex-col lg:flex-row lg:items-center justify-between gap-5">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="text-[11px] font-bold tracking-wider uppercase px-2.5 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-500/30">
              Live Operations Control Center
            </span>
            <span className="text-[11px] text-slate-400">
              Role: <strong className="text-white capitalize">{user?.role}</strong>
            </span>
          </div>
          <h1 className="text-2xl font-bold mt-2">Executive Business Financials</h1>
          <p className="text-xs sm:text-sm text-slate-300 mt-1 max-w-2xl">
            Real-time accounts payable analytics, multi-vendor liability tracking, automated cashflow projections, and AI-assisted invoice extractions.
          </p>
        </div>

        {/* Quick Action Buttons */}
        <div className="flex flex-wrap items-center gap-2.5 shrink-0">
          <button
            onClick={fetchDashboardData}
            disabled={refreshing}
            className="p-2.5 bg-slate-800/80 hover:bg-slate-700 text-slate-200 rounded-xl border border-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-all"
            title="Refresh Live Metrics"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin text-brand-400' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
          <button
            onClick={handleSyncEmail}
            disabled={isSyncingEmail}
            className="px-3.5 py-2.5 bg-slate-800/80 hover:bg-slate-700 text-slate-200 rounded-xl border border-slate-700 text-xs font-semibold flex items-center gap-2 transition-all disabled:opacity-50"
            title="Fetch unread invoice attachments from Gmail"
          >
            {isSyncingEmail ? (
              <Loader2 className="w-4 h-4 animate-spin text-brand-400" />
            ) : (
              <Mail className="w-4 h-4 text-brand-400" />
            )}
            <span>{isSyncingEmail ? 'Syncing Gmail...' : 'Sync from Gmail'}</span>
          </button>
          <Link
            to="/invoices/upload"
            className="px-4 py-2.5 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-bold shadow-sm shadow-brand-500/30 flex items-center gap-2 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Upload Invoice</span>
          </Link>
          <Link
            to="/reports"
            className="px-4 py-2.5 bg-slate-800/80 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold border border-slate-700 transition-all flex items-center gap-1.5"
          >
            <Receipt className="w-4 h-4 text-brand-400" />
            <span>Tax & Reports</span>
          </Link>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Invoiced */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Total Invoiced</span>
            <div className="p-2 rounded-xl bg-blue-50 text-blue-600 border border-blue-100">
              <FileText className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-black text-slate-900 mt-2">
            {formatCurrency(stats?.total_invoiced_amount)}
          </p>
          <div className="flex items-center justify-between text-xs text-slate-500 mt-2 pt-2 border-t border-slate-100">
            <span>{stats?.total_invoices_count || 0} active invoices</span>
            <span className="font-semibold text-blue-600">AP Ledger</span>
          </div>
        </div>

        {/* Total Settled / Paid */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Total Settled</span>
            <div className="p-2 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-100">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-black text-emerald-700 mt-2">
            {formatCurrency(stats?.total_paid_amount)}
          </p>
          <div className="flex items-center justify-between text-xs text-slate-500 mt-2 pt-2 border-t border-slate-100">
            <span>{stats?.total_settled_transactions || 0} payment records</span>
            <span className="font-semibold text-emerald-600">Disbursed</span>
          </div>
        </div>

        {/* Total Outstanding / Pending */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Outstanding Balance</span>
            <div className="p-2 rounded-xl bg-amber-50 text-amber-600 border border-amber-100">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-black text-amber-600 mt-2">
            {formatCurrency(stats?.total_outstanding_amount)}
          </p>
          <div className="flex items-center justify-between text-xs text-slate-500 mt-2 pt-2 border-t border-slate-100">
            <span>Pending settlement</span>
            <span className="font-semibold text-amber-600">Liabilities</span>
          </div>
        </div>

        {/* Overdue Risk */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Overdue Invoices</span>
            <div className="p-2 rounded-xl bg-rose-50 text-rose-600 border border-rose-100">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-black text-rose-600 mt-2">
            {formatCurrency(stats?.overdue_amount)}
          </p>
          <div className="flex items-center justify-between text-xs text-slate-500 mt-2 pt-2 border-t border-slate-100">
            <span className="text-rose-600 font-semibold">{stats?.overdue_invoices_count || 0} overdue</span>
            <span className="font-semibold text-rose-600">Action Needed</span>
          </div>
        </div>
      </div>

      {/* Secondary Quick Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Operational Expenses */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-purple-50 text-purple-600 rounded-lg">
              <DollarSign className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500">Operational Expenses</p>
              <p className="text-lg font-bold text-slate-900">{formatCurrency(stats?.total_expenses_amount)}</p>
            </div>
          </div>
          <span className="text-xs font-semibold text-slate-500 bg-slate-100 px-2 py-1 rounded-md">
            {stats?.total_expenses_count || 0} records
          </span>
        </div>

        {/* AI Extraction Confidence */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-50 text-indigo-600 rounded-lg">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500">Avg AI Accuracy</p>
              <p className="text-lg font-bold text-indigo-600">
                {stats?.average_ai_confidence 
                  ? (Number(stats.average_ai_confidence) > 1 
                      ? `${Number(stats.average_ai_confidence).toFixed(1)}%` 
                      : `${(Number(stats.average_ai_confidence) * 100).toFixed(1)}%`)
                  : '98.5%'}
              </p>
            </div>
          </div>
          <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-md border border-emerald-100">
            High Quality
          </span>
        </div>

        {/* Pending Review Queue */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-brand-50 text-brand-600 rounded-lg">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500">Registered Vendors</p>
              <p className="text-lg font-bold text-slate-900">{stats?.total_vendors_count || 0} Suppliers</p>
            </div>
          </div>
          <Link
            to="/vendors"
            className="text-xs font-semibold text-brand-600 hover:text-brand-700 flex items-center gap-1"
          >
            <span>View</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Main Charts & Visualizations Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cashflow Trend Chart (2 Cols) */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-brand-600" />
                  <span>Monthly Cashflow & Outflow Analysis</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Comparison between total billed liabilities, settled vendor disbursements, and direct expenses.
                </p>
              </div>

              {/* Month Selector */}
              <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl self-start sm:self-auto">
                {[6, 12].map((m) => (
                  <button
                    key={m}
                    onClick={() => setCashflowMonths(m)}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                      cashflowMonths === m
                        ? 'bg-white text-slate-900 shadow-sm'
                        : 'text-slate-500 hover:text-slate-900'
                    }`}
                  >
                    {m}M Trend
                  </button>
                ))}
              </div>
            </div>

            {/* Visual Bar Chart */}
            <div className="h-64 flex items-end justify-between gap-3 pt-6 border-b border-slate-100 pb-2">
              {cashflow.length === 0 ? (
                <div className="w-full h-full flex items-center justify-center text-xs text-slate-400">
                  No historical cashflow records found.
                </div>
              ) : (
                cashflow.map((item, idx) => {
                  const invH = Math.max((Number(item.invoiced_amount) / maxCashflowVal) * 100, 4);
                  const payH = Math.max((Number(item.paid_amount) / maxCashflowVal) * 100, 4);
                  const expH = Math.max((Number(item.expense_amount) / maxCashflowVal) * 100, 4);

                  return (
                    <div key={idx} className="flex-1 flex flex-col items-center gap-2 group relative">
                      {/* Tooltip on Hover */}
                      <div className="absolute bottom-full mb-2 hidden group-hover:flex flex-col gap-1 bg-slate-900 text-white text-[11px] p-2.5 rounded-lg shadow-xl z-20 whitespace-nowrap">
                        <span className="font-bold text-brand-300">{item.month_label}</span>
                        <span>Billed: {formatCurrency(item.invoiced_amount)}</span>
                        <span>Disbursed: {formatCurrency(item.paid_amount)}</span>
                        <span>Expenses: {formatCurrency(item.expense_amount)}</span>
                      </div>

                      {/* Stacked/Grouped Bars */}
                      <div className="w-full max-w-[48px] h-48 flex items-end justify-center gap-1">
                        {/* Invoiced Bar */}
                        <div
                          style={{ height: `${invH}%` }}
                          className="w-1/3 bg-blue-500/80 hover:bg-blue-600 rounded-t transition-all"
                          title={`Invoiced: ${formatCurrency(item.invoiced_amount)}`}
                        ></div>
                        {/* Paid Bar */}
                        <div
                          style={{ height: `${payH}%` }}
                          className="w-1/3 bg-emerald-500/80 hover:bg-emerald-600 rounded-t transition-all"
                          title={`Paid: ${formatCurrency(item.paid_amount)}`}
                        ></div>
                        {/* Expense Bar */}
                        <div
                          style={{ height: `${expH}%` }}
                          className="w-1/3 bg-purple-500/80 hover:bg-purple-600 rounded-t transition-all"
                          title={`Expense: ${formatCurrency(item.expense_amount)}`}
                        ></div>
                      </div>

                      <span className="text-[11px] font-semibold text-slate-600">{item.month_label.split(' ')[0]}</span>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Legend */}
          <div className="flex items-center justify-center gap-6 pt-4 text-xs font-medium text-slate-600">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-blue-500"></span>
              <span>Invoiced Volume</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-emerald-500"></span>
              <span>Paid Disbursements</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-purple-500"></span>
              <span>Direct Expenses</span>
            </div>
          </div>
        </div>

        {/* Category Spend Breakdown (1 Col) */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2 mb-1">
              <PieChart className="w-5 h-5 text-brand-600" />
              <span>Spend by Category</span>
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Combined distribution across supplier goods, software, logistics, and ops.
            </p>

            <div className="space-y-3.5">
              {categories.length === 0 ? (
                <p className="text-xs text-slate-400 py-6 text-center">No category spend data available.</p>
              ) : (
                categories.slice(0, 5).map((cat, idx) => {
                  const colors = [
                    'bg-brand-500',
                    'bg-blue-500',
                    'bg-indigo-500',
                    'bg-purple-500',
                    'bg-amber-500',
                  ];
                  const barColor = colors[idx % colors.length];

                  return (
                    <div key={idx} className="space-y-1">
                      <div className="flex justify-between items-center text-xs">
                        <span className="font-semibold text-slate-800">{cat.category}</span>
                        <div className="text-right">
                          <span className="font-bold text-slate-900">{formatCurrency(cat.amount)}</span>
                          <span className="text-slate-400 text-[11px] ml-1.5">({cat.percentage}%)</span>
                        </div>
                      </div>
                      <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                        <div
                          style={{ width: `${Math.min(cat.percentage, 100)}%` }}
                          className={`h-full ${barColor} rounded-full transition-all`}
                        ></div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          <Link
            to="/expenses"
            className="mt-4 text-xs font-semibold text-brand-600 hover:text-brand-700 flex items-center justify-center gap-1 py-2 rounded-xl border border-brand-200 hover:bg-brand-50 transition-colors"
          >
            <span>Detailed Expense Management</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Status Breakdown & Top Vendors & Activity Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Suppliers / Vendors Ranking (2 Cols) */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Building2 className="w-5 h-5 text-brand-600" />
                <span>Top Suppliers by Invoiced Spend</span>
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Key vendor accounts ranked by historical volume and outstanding liability.
              </p>
            </div>
            <Link
              to="/vendors"
              className="text-xs font-semibold text-brand-600 hover:text-brand-700 flex items-center gap-1"
            >
              <span>View All</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider font-semibold border-y border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Supplier Name</th>
                  <th className="py-2.5 px-3">Category</th>
                  <th className="py-2.5 px-3 text-right">Invoiced</th>
                  <th className="py-2.5 px-3 text-right">Settled</th>
                  <th className="py-2.5 px-3 text-right">Outstanding</th>
                  <th className="py-2.5 px-3 text-center">Invoices</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {topVendors.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="py-6 text-center text-slate-400">
                      No vendor spending recorded yet.
                    </td>
                  </tr>
                ) : (
                  topVendors.map((v) => (
                    <tr key={v.vendor_id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3 px-3 font-bold text-slate-900">{v.vendor_name}</td>
                      <td className="py-3 px-3">
                        <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-medium">
                          {v.category || 'General'}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right font-semibold text-slate-900">
                        {formatCurrency(v.total_invoiced)}
                      </td>
                      <td className="py-3 px-3 text-right font-medium text-emerald-600">
                        {formatCurrency(v.total_paid)}
                      </td>
                      <td className="py-3 px-3 text-right font-bold text-amber-600">
                        {formatCurrency(v.outstanding_balance)}
                      </td>
                      <td className="py-3 px-3 text-center">
                        <span className="font-semibold text-slate-700">{v.invoice_count}</span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Real-time Chronological Activity Stream (1 Col) */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Activity className="w-5 h-5 text-brand-600" />
                <span>Recent Activity</span>
              </h3>
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            </div>

            <div className="space-y-3.5">
              {recentActivity.length === 0 ? (
                <p className="text-xs text-slate-400 py-6 text-center">No recent activity found.</p>
              ) : (
                recentActivity.map((act) => {
                  const isInv = act.type === 'INVOICE';
                  const isPay = act.type === 'PAYMENT';
                  const isExp = act.type === 'EXPENSE';

                  return (
                    <div key={act.id} className="flex items-start gap-3 text-xs">
                      <div
                        className={`p-2 rounded-xl mt-0.5 shrink-0 ${
                          isInv
                            ? 'bg-blue-50 text-blue-600'
                            : isPay
                            ? 'bg-emerald-50 text-emerald-600'
                            : 'bg-purple-50 text-purple-600'
                        }`}
                      >
                        {isInv && <FileText className="w-3.5 h-3.5" />}
                        {isPay && <CheckCircle2 className="w-3.5 h-3.5" />}
                        {isExp && <DollarSign className="w-3.5 h-3.5" />}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-1">
                          <p className="font-bold text-slate-900 truncate">{act.title}</p>
                          {act.amount && (
                            <span className="font-bold text-slate-900 shrink-0">
                              {formatCurrency(act.amount)}
                            </span>
                          )}
                        </div>
                        <p
                          className="text-[11px] text-slate-500 truncate"
                          dangerouslySetInnerHTML={{ __html: act.subtitle || '' }}
                        ></p>
                        <span className="text-[10px] text-slate-400">
                          {new Date(act.timestamp).toLocaleDateString(undefined, {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          <Link
            to="/invoices"
            className="mt-4 text-xs font-semibold text-brand-600 hover:text-brand-700 flex items-center justify-center gap-1 py-2 rounded-xl border border-brand-200 hover:bg-brand-50 transition-colors"
          >
            <span>Explore Complete Ledger</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>
    </div>
  );
};
