import React, { useState, useEffect } from 'react';
import { reportApi } from '../services/api';
import {
  FileSpreadsheet,
  Download,
  Calendar,
  Receipt,
  FileText,
  CreditCard,
  Building2,
  Filter,
  CheckCircle2,
  RefreshCw,
  Copy,
  Check,
  Percent,
} from 'lucide-react';

export const Reports = () => {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [taxSummary, setTaxSummary] = useState(null);
  const [loadingTax, setLoadingTax] = useState(false);
  const [downloading, setDownloading] = useState({
    invoices: false,
    expenses: false,
    payments: false,
  });
  const [copiedGstin, setCopiedGstin] = useState(null);

  const fetchTaxSummary = async () => {
    try {
      setLoadingTax(true);
      const params = {};
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      const res = await reportApi.getTaxSummary(params);
      setTaxSummary(res.data);
    } catch (err) {
      console.error('Failed to load tax summary:', err);
    } finally {
      setLoadingTax(false);
    }
  };

  useEffect(() => {
    fetchTaxSummary();
  }, [startDate, endDate]);

  const handleExport = async (type) => {
    try {
      setDownloading((prev) => ({ ...prev, [type]: true }));
      const params = {};
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;

      if (type === 'invoices') {
        await reportApi.downloadInvoicesCsv(params);
      } else if (type === 'expenses') {
        await reportApi.downloadExpensesCsv(params);
      } else if (type === 'payments') {
        await reportApi.downloadPaymentsCsv(params);
      }
    } catch (err) {
      console.error(`Failed to export ${type}:`, err);
      alert(`Export failed for ${type}. Please try again.`);
    } finally {
      setDownloading((prev) => ({ ...prev, [type]: false }));
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedGstin(text);
    setTimeout(() => setCopiedGstin(null), 2000);
  };

  const formatCurrency = (val) => {
    const num = Number(val || 0);
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(num);
  };

  const setPreset = (preset) => {
    const today = new Date();
    if (preset === 'THIS_MONTH') {
      const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
      setStartDate(firstDay.toISOString().split('T')[0]);
      setEndDate(today.toISOString().split('T')[0]);
    } else if (preset === 'LAST_MONTH') {
      const firstDay = new Date(today.getFullYear(), today.getMonth() - 1, 1);
      const lastDay = new Date(today.getFullYear(), today.getMonth(), 0);
      setStartDate(firstDay.toISOString().split('T')[0]);
      setEndDate(lastDay.toISOString().split('T')[0]);
    } else if (preset === 'FY_2026') {
      setStartDate('2026-04-01');
      setEndDate('2027-03-31');
    } else if (preset === 'ALL_TIME') {
      setStartDate('');
      setEndDate('');
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2.5">
            <FileSpreadsheet className="w-6 h-6 text-brand-600" />
            <span>Financial Reports & Tax Intelligence</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Generate compliant RFC 4180 CSV audit reports and calculate vendor Input Tax Credits (ITC) for GST filings.
          </p>
        </div>

        {/* Refresh button */}
        <button
          onClick={fetchTaxSummary}
          disabled={loadingTax}
          className="p-2.5 bg-white hover:bg-slate-50 text-slate-700 rounded-xl border border-slate-200 text-xs font-semibold flex items-center gap-1.5 shadow-sm self-start sm:self-auto"
        >
          <RefreshCw className={`w-4 h-4 ${loadingTax ? 'animate-spin text-brand-600' : ''}`} />
          <span>Refresh Data</span>
        </button>
      </div>

      {/* Date Range & Filter Controls */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
            <Calendar className="w-4 h-4 text-brand-600" />
            <span>Date Range:</span>
          </div>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          />
          <span className="text-slate-400 text-xs font-medium">to</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          />
        </div>

        {/* Quick Date Presets */}
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            onClick={() => setPreset('ALL_TIME')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              !startDate && !endDate
                ? 'bg-slate-900 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            All Time
          </button>
          <button
            onClick={() => setPreset('THIS_MONTH')}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 text-slate-600 hover:bg-slate-200 transition-all"
          >
            This Month
          </button>
          <button
            onClick={() => setPreset('LAST_MONTH')}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 text-slate-600 hover:bg-slate-200 transition-all"
          >
            Last Month
          </button>
          <button
            onClick={() => setPreset('FY_2026')}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 text-slate-600 hover:bg-slate-200 transition-all"
          >
            FY 2026-27
          </button>
        </div>
      </div>

      {/* CSV Export Quick Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Invoices Export Card */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between hover:border-blue-200 hover:shadow-md transition-all">
          <div>
            <div className="flex items-center justify-between">
              <div className="p-3 rounded-xl bg-blue-50 text-blue-600 border border-blue-100">
                <FileText className="w-6 h-6" />
              </div>
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-blue-50 text-blue-700">
                Accounts Payable
              </span>
            </div>
            <h3 className="text-base font-bold text-slate-900 mt-4">Invoices Master Ledger</h3>
            <p className="text-xs text-slate-500 mt-1">
              Full dataset including line item sums, GST amounts, due dates, statuses, and AI confidence scores.
            </p>
          </div>
          <button
            onClick={() => handleExport('invoices')}
            disabled={downloading.invoices}
            className="mt-5 w-full py-2.5 px-4 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-2 shadow-sm transition-all"
          >
            {downloading.invoices ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            <span>Export Invoices (.CSV)</span>
          </button>
        </div>

        {/* Expenses Export Card */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between hover:border-purple-200 hover:shadow-md transition-all">
          <div>
            <div className="flex items-center justify-between">
              <div className="p-3 rounded-xl bg-purple-50 text-purple-600 border border-purple-100">
                <Receipt className="w-6 h-6" />
              </div>
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-purple-50 text-purple-700">
                Operations
              </span>
            </div>
            <h3 className="text-base font-bold text-slate-900 mt-4">Operational Expenses</h3>
            <p className="text-xs text-slate-500 mt-1">
              Direct company expenditures classified by expense categories, payment channels, and receipt dates.
            </p>
          </div>
          <button
            onClick={() => handleExport('expenses')}
            disabled={downloading.expenses}
            className="mt-5 w-full py-2.5 px-4 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-2 shadow-sm transition-all"
          >
            {downloading.expenses ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            <span>Export Expenses (.CSV)</span>
          </button>
        </div>

        {/* Payments Export Card */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between hover:border-emerald-200 hover:shadow-md transition-all">
          <div>
            <div className="flex items-center justify-between">
              <div className="p-3 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-100">
                <CreditCard className="w-6 h-6" />
              </div>
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700">
                Disbursements
              </span>
            </div>
            <h3 className="text-base font-bold text-slate-900 mt-4">Settlement Transactions</h3>
            <p className="text-xs text-slate-500 mt-1">
              Bank transfers, UPI receipts, NEFT/RTGS references, and invoice reconciliation timestamps.
            </p>
          </div>
          <button
            onClick={() => handleExport('payments')}
            disabled={downloading.payments}
            className="mt-5 w-full py-2.5 px-4 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-2 shadow-sm transition-all"
          >
            {downloading.payments ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            <span>Export Settlements (.CSV)</span>
          </button>
        </div>
      </div>

      {/* GST & Tax Accounting Summary Section */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Percent className="w-5 h-5 text-brand-600" />
              <span>Tax Summary & Input Tax Credit (ITC) Report</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Breakdown of GST/Tax collected across registered supplier accounts for statutory compliance.
            </p>
          </div>
          <span className="text-xs font-semibold px-3 py-1 rounded-full bg-slate-100 text-slate-700">
            {taxSummary?.total_invoices || 0} Processed Invoices
          </span>
        </div>

        {/* Summary Metric Badges */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
            <span className="text-xs font-medium text-slate-500">Taxable Subtotal (Net)</span>
            <p className="text-xl font-black text-slate-900 mt-1">
              {formatCurrency(taxSummary?.total_subtotal)}
            </p>
          </div>
          <div className="p-4 rounded-xl bg-brand-50 border border-brand-200/80">
            <span className="text-xs font-semibold text-brand-700">Total Input Tax Credit (ITC)</span>
            <p className="text-xl font-black text-brand-700 mt-1">
              {formatCurrency(taxSummary?.total_tax_amount)}
            </p>
          </div>
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
            <span className="text-xs font-medium text-slate-500">Total Gross Billed</span>
            <p className="text-xl font-black text-slate-900 mt-1">
              {formatCurrency(taxSummary?.total_gross_amount)}
            </p>
          </div>
        </div>

        {/* Vendor Breakdown Table */}
        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider font-semibold border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Supplier / Vendor</th>
                <th className="py-3 px-4">GSTIN Identification</th>
                <th className="py-3 px-4 text-center">Invoices</th>
                <th className="py-3 px-4 text-right">Taxable Subtotal</th>
                <th className="py-3 px-4 text-right">GST / Tax Amount</th>
                <th className="py-3 px-4 text-right">Total Gross</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {!taxSummary?.vendors_breakdown || taxSummary.vendors_breakdown.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-slate-400">
                    No supplier tax records found for the selected range.
                  </td>
                </tr>
              ) : (
                taxSummary.vendors_breakdown.map((v) => (
                  <tr key={v.vendor_id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 font-bold text-slate-900">{v.vendor_name}</td>
                    <td className="py-3.5 px-4 font-mono text-slate-600">
                      {v.gstin ? (
                        <button
                          onClick={() => copyToClipboard(v.gstin)}
                          className="flex items-center gap-1.5 hover:text-brand-600 transition-colors group"
                          title="Click to copy GSTIN"
                        >
                          <span>{v.gstin}</span>
                          {copiedGstin === v.gstin ? (
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                          ) : (
                            <Copy className="w-3.5 h-3.5 text-slate-400 group-hover:text-brand-600" />
                          )}
                        </button>
                      ) : (
                        <span className="text-slate-400 italic">Unregistered</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-center font-semibold text-slate-700">
                      {v.invoice_count}
                    </td>
                    <td className="py-3.5 px-4 text-right font-medium text-slate-700">
                      {formatCurrency(v.subtotal)}
                    </td>
                    <td className="py-3.5 px-4 text-right font-bold text-brand-600">
                      {formatCurrency(v.tax_amount)}
                    </td>
                    <td className="py-3.5 px-4 text-right font-black text-slate-900">
                      {formatCurrency(v.total_gross)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
