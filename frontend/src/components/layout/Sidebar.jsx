import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  Building2,
  Receipt,
  CreditCard,
  BarChart3,
  ShieldCheck,
  Settings,
  LogOut,
  FileUp,
  AlertTriangle,
  X
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { StatusBadge } from '../common/StatusBadge';

export const Sidebar = () => {
  const { user, logout, hasRole } = useAuth();
  const navigate = useNavigate();
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  const confirmLogout = () => {
    setShowLogoutConfirm(false);
    logout();
    navigate('/login');
  };

  const navItems = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/invoices', label: 'Invoices', icon: FileText },
    { to: '/vendors', label: 'Vendors', icon: Building2 },
    { to: '/expenses', label: 'Expenses', icon: Receipt },
    { to: '/payments', label: 'Payments', icon: CreditCard },
    { to: '/reports', label: 'Reports', icon: BarChart3 },
    ...(hasRole('ADMIN') ? [{ to: '/audit-logs', label: 'Audit Logs', icon: ShieldCheck }] : []),
    { to: '/settings', label: 'Settings', icon: Settings },
  ];

  return (
    <>
      <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 border-r border-slate-800 select-none">
        {/* Brand Header */}
        <div className="h-16 flex items-center gap-3 px-6 border-b border-slate-800/80 bg-slate-950/40">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white font-bold shadow-lg shadow-brand-600/30 border border-brand-400/20">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <div className="font-bold text-white tracking-tight flex items-center gap-1.5">
              SmartInvoice
              <span className="text-[10px] uppercase font-semibold px-1.5 py-0.2 bg-brand-500/20 text-brand-300 rounded border border-brand-500/30">
                SaaS
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">Business Automation</p>
          </div>
        </div>

        {/* Quick Action Upload (Staff & Admin) */}
        {hasRole(['ADMIN', 'STAFF']) && (
          <div className="px-4 pt-5 pb-2">
            <NavLink
              to="/invoices/upload"
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-sm font-semibold shadow-md shadow-brand-600/20 transition-all duration-150 active:scale-[0.98]"
            >
              <FileUp className="w-4 h-4" />
              <span>Upload Invoice</span>
            </NavLink>
          </div>
        )}

        {/* Navigation Links */}
        <nav className="flex-1 px-3 py-3 space-y-1 overflow-y-auto">
          <div className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Platform
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-brand-600/20 text-brand-300 font-semibold border-l-2 border-brand-500 pl-[10px]'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* User Footer Profile */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-950/30">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-600 to-indigo-600 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-md">
                {user?.full_name?.charAt(0) || 'S'}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold text-white truncate">{user?.full_name || 'Admin'}</p>
                <div className="mt-0.5">
                  <StatusBadge status={user?.role || 'ADMIN'} />
                </div>
              </div>
            </div>
            <button
              onClick={() => setShowLogoutConfirm(true)}
              title="Sign Out"
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors shrink-0"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Logout Confirmation Modal */}
      {showLogoutConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-sm w-full shadow-2xl relative text-left">
            <button
              onClick={() => setShowLogoutConfirm(false)}
              className="absolute top-4 right-4 p-1 text-slate-400 hover:text-slate-200 rounded-lg transition-colors"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="w-12 h-12 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mb-4">
              <AlertTriangle className="w-6 h-6" />
            </div>

            <h3 className="text-lg font-bold text-white tracking-tight">Sign out of SmartInvoice?</h3>
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
              Are you sure you want to end your current session? You will need to sign in again to access invoices and financials.
            </p>

            <div className="mt-6 flex items-center justify-end gap-2.5">
              <button
                type="button"
                onClick={() => setShowLogoutConfirm(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmLogout}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-rose-600 hover:bg-rose-500 shadow-lg shadow-rose-600/30 transition-colors"
              >
                Yes, Sign Out
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
