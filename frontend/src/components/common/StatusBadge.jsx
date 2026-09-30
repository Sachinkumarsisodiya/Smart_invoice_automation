import React from 'react';

export const StatusBadge = ({ status, type = 'invoice' }) => {
  const getBadgeStyle = () => {
    switch (status) {
      case 'APPROVED':
      case 'PAID':
      case 'SUCCESS':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'PENDING_REVIEW':
      case 'PENDING':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'PARTIALLY_PAID':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'PROCESSING':
        return 'bg-indigo-50 text-indigo-700 border-indigo-200 animate-pulse';
      case 'REJECTED':
      case 'FAILED':
      case 'OVERDUE':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'DUPLICATE':
        return 'bg-rose-100 text-rose-800 border-rose-300 font-bold';
      case 'ADMIN':
        return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'STAFF':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'VIEWER':
        return 'bg-slate-100 text-slate-700 border-slate-200';
      default:
        return 'bg-slate-50 text-slate-600 border-slate-200';
    }
  };

  const formatText = (text) => {
    if (!text) return '';
    return text.replace(/_/g, ' ');
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getBadgeStyle()}`}
    >
      {formatText(status)}
    </span>
  );
};
