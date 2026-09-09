import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, User, Key, Bell, Database, Server, Mail, RefreshCw, Play, CheckCircle2, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { StatusBadge } from '../components/common/StatusBadge';
import { systemApi } from '../services/api';

export const Settings = () => {
  const { user } = useAuth();
  const [health, setHealth] = useState(null);
  const [celeryStatus, setCeleryStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState({ due: false, reminder: false });
  const [triggerMsg, setTriggerMsg] = useState(null);

  const fetchSystemStatus = async () => {
    try {
      setLoading(true);
      const [healthRes, celeryRes] = await Promise.all([
        systemApi.getHealth(),
        systemApi.getCeleryStatus(),
      ]);
      setHealth(healthRes.data);
      setCeleryStatus(celeryRes.data);
    } catch (err) {
      console.error('Failed to fetch system status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSystemStatus();
  }, []);

  const handleTriggerDueScan = async () => {
    try {
      setTriggering((prev) => ({ ...prev, due: true }));
      const res = await systemApi.triggerDueDateScan();
      setTriggerMsg({ type: 'success', text: `Due date scan completed: ${res.data.details.updated} overdue invoices updated.` });
      setTimeout(() => setTriggerMsg(null), 5000);
    } catch (err) {
      setTriggerMsg({ type: 'error', text: 'Failed to trigger overdue scan.' });
    } finally {
      setTriggering((prev) => ({ ...prev, due: false }));
    }
  };

  const handleTriggerReminderScan = async () => {
    try {
      setTriggering((prev) => ({ ...prev, reminder: true }));
      const res = await systemApi.triggerReminderScan();
      setTriggerMsg({ type: 'success', text: `Payment reminder scan completed: ${res.data.details.sent} emails dispatched (${res.data.details.skipped} already sent today).` });
      setTimeout(() => setTriggerMsg(null), 5000);
    } catch (err) {
      setTriggerMsg({ type: 'error', text: 'Failed to trigger reminder scan.' });
    } finally {
      setTriggering((prev) => ({ ...prev, reminder: false }));
    }
  };

  return (
    <div className="space-y-6 max-w-4xl pb-12">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">System & Automation Settings</h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Manage organization credentials, background automation workers, and email dispatch configuration.
          </p>
        </div>

        <button
          onClick={fetchSystemStatus}
          disabled={loading}
          className="p-2.5 bg-white hover:bg-slate-50 text-slate-700 rounded-xl border border-slate-200 text-xs font-semibold flex items-center gap-1.5 shadow-sm"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-brand-600' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {triggerMsg && (
        <div
          className={`p-4 rounded-xl text-xs font-semibold flex items-center gap-2 ${
            triggerMsg.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              : 'bg-rose-50 text-rose-800 border border-rose-200'
          }`}
        >
          {triggerMsg.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          <span>{triggerMsg.text}</span>
        </div>
      )}

      {/* User Profile Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
        <div>
          <h2 className="text-sm font-bold text-slate-800 mb-1 flex items-center gap-2">
            <User className="w-4 h-4 text-brand-600" />
            <span>User Profile & Access Role</span>
          </h2>
          <p className="text-xs text-slate-500 mb-4">Your current authenticated session credentials.</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-slate-400 block mb-0.5 font-medium">Full Name</span>
              <span className="font-bold text-slate-900">{user?.full_name}</span>
            </div>
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-slate-400 block mb-0.5 font-medium">Email Address</span>
              <span className="font-bold text-slate-900">{user?.email}</span>
            </div>
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-slate-400 block mb-0.5 font-medium">Assigned Role</span>
              <div className="mt-1"><StatusBadge status={user?.role} /></div>
            </div>
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-slate-400 block mb-0.5 font-medium">Account Status</span>
              <span className="font-bold text-emerald-600">Active</span>
            </div>
          </div>
        </div>
      </div>

      {/* Background Automation & Celery Health Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-5">
        <div>
          <h2 className="text-sm font-bold text-slate-800 mb-1 flex items-center gap-2">
            <Server className="w-4 h-4 text-brand-600" />
            <span>Background Automation & Celery Beat</span>
          </h2>
          <p className="text-xs text-slate-500">
            Automated invoice due-date monitoring and recurring payment reminder dispatch engine.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
            <span className="text-slate-400 block mb-1 font-medium">Database Health</span>
            <span className="font-bold capitalize text-emerald-600">{health?.database || 'healthy'}</span>
          </div>
          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
            <span className="text-slate-400 block mb-1 font-medium">Redis Connection</span>
            <span className="font-bold capitalize text-slate-800">{health?.redis || 'connected'}</span>
          </div>
          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
            <span className="text-slate-400 block mb-1 font-medium">Celery Timezone</span>
            <span className="font-bold font-mono text-slate-800">{celeryStatus?.timezone || 'UTC'}</span>
          </div>
        </div>

        {/* Scheduled Tasks List */}
        <div className="space-y-2">
          <span className="text-xs font-bold text-slate-700 block">Configured Beat Automation Schedule:</span>
          {celeryStatus?.beat_schedule?.map((item, idx) => (
            <div key={idx} className="p-3 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between text-xs">
              <div>
                <p className="font-bold text-slate-800">{item.name}</p>
                <p className="text-[11px] font-mono text-slate-400 mt-0.5">{item.task}</p>
              </div>
              <span className="px-2 py-0.5 bg-brand-50 text-brand-700 font-semibold rounded-md text-[11px] border border-brand-200">
                {item.schedule}
              </span>
            </div>
          ))}
        </div>

        {/* Manual Trigger Buttons for Admin */}
        {user?.role === 'ADMIN' && (
          <div className="pt-4 border-t border-slate-100 flex flex-wrap items-center gap-3">
            <button
              onClick={handleTriggerDueScan}
              disabled={triggering.due}
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-sm"
            >
              {triggering.due ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
              <span>Run Overdue Invoices Scan Now</span>
            </button>

            <button
              onClick={handleTriggerReminderScan}
              disabled={triggering.reminder}
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-sm"
            >
              {triggering.reminder ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
              <span>Run Payment Reminders Scan Now</span>
            </button>
          </div>
        )}
      </div>

      {/* Email & AI Provider Mode Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
        <div>
          <h2 className="text-sm font-bold text-slate-800 mb-1 flex items-center gap-2">
            <Mail className="w-4 h-4 text-brand-600" />
            <span>Email & AI Service Modes</span>
          </h2>
          <p className="text-xs text-slate-500">Configured via backend `.env` variables (Zero credentials exposed).</p>
        </div>

        <div className="space-y-3 text-xs">
          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
            <div>
              <p className="font-bold text-slate-800">Email Dispatch Provider</p>
              <p className="text-slate-500 text-[11px] mt-0.5">
                Current mode: <strong className="uppercase">{health?.email_provider || 'MOCK'}</strong> (Local mock queue active)
              </p>
            </div>
            <span className="px-2.5 py-1 bg-brand-50 text-brand-700 font-bold rounded-lg text-[11px] border border-brand-200">
              {health?.email_provider?.toUpperCase() || 'MOCK'}
            </span>
          </div>

          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
            <div>
              <p className="font-bold text-slate-800">AI Extraction Provider</p>
              <p className="text-slate-500 text-[11px] mt-0.5">
                Current mode: <strong className="uppercase">{health?.ai_provider || 'MOCK'}</strong>
              </p>
            </div>
            <span className="px-2.5 py-1 bg-brand-50 text-brand-700 font-bold rounded-lg text-[11px] border border-brand-200">
              {health?.ai_provider?.toUpperCase() || 'MOCK'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
