import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  UploadCloud,
  File,
  AlertCircle,
  CheckCircle2,
  ArrowLeft,
  Loader2,
  FileText,
  Eye,
  Check,
} from 'lucide-react';
import { invoiceService } from '../services/invoiceService';

export const UploadInvoice = () => {
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');
  const [uploadResult, setUploadResult] = useState(null);

  const navigate = useNavigate();

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleSelectedFile(e.target.files[0]);
    }
  };

  const handleSelectedFile = (selected) => {
    setError('');
    setUploadResult(null);

    const ext = selected.name.split('.').pop().toLowerCase();
    const allowed = ['pdf', 'png', 'jpg', 'jpeg'];
    if (!allowed.includes(ext)) {
      setError(`Invalid format '.${ext}'. Only PDF, PNG, and JPG files are supported.`);
      return;
    }

    if (selected.size > 15 * 1024 * 1024) {
      setError(`File size (${(selected.size / (1024 * 1024)).toFixed(1)}MB) exceeds 15MB limit.`);
      return;
    }

    setFile(selected);
  };

  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);
    setError('');
    setUploadProgress(10);

    try {
      const result = await invoiceService.uploadInvoice(file, null, (progressEvent) => {
        if (progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percent);
        }
      });
      setUploadResult(result);
    } catch (err) {
      console.error('Upload failed:', err);
      setError(err.response?.data?.error?.message || 'Failed to upload and process invoice.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex items-center gap-3">
        <Link
          to="/invoices"
          className="p-2 rounded-lg bg-white border border-slate-200 text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Upload & Ingest Invoice</h2>
          <p className="text-xs text-slate-500">
            Automated file validation, PyMuPDF digital text extraction, and private storage.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
          <span>{error}</span>
        </div>
      )}

      {/* Upload Zone */}
      {!uploadResult ? (
        <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-sm space-y-6">
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-2xl p-10 text-center transition-all cursor-pointer ${
              dragActive
                ? 'border-brand-500 bg-brand-50/50 scale-[1.01]'
                : 'border-slate-300 hover:border-brand-400 bg-slate-50/40'
            }`}
          >
            <input
              type="file"
              id="file-upload"
              accept=".pdf,.png,.jpg,.jpeg"
              onChange={handleFileChange}
              className="hidden"
            />
            <label htmlFor="file-upload" className="cursor-pointer block">
              <div className="w-14 h-14 rounded-2xl bg-brand-50 text-brand-600 flex items-center justify-center mx-auto mb-3 shadow-inner">
                <UploadCloud className="w-7 h-7" />
              </div>
              <p className="text-sm font-bold text-slate-800">
                {file ? file.name : 'Click to select or drag & drop invoice'}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                Supports PDF, JPG, PNG (Max file size: 15MB)
              </p>
            </label>
          </div>

          {file && (
            <div className="p-4 bg-brand-50/60 border border-brand-200 rounded-xl flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-brand-100 text-brand-700 rounded-lg">
                  <File className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-xs font-bold text-slate-800">{file.name}</p>
                  <p className="text-[11px] text-slate-500">{(file.size / 1024).toFixed(1)} KB • Ready for extraction</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setFile(null)}
                className="text-xs text-slate-400 hover:text-rose-500 font-medium px-2 py-1"
              >
                Change
              </button>
            </div>
          )}

          {isUploading && (
            <div className="space-y-2">
              <div className="flex justify-between text-xs text-slate-500 font-medium">
                <span>Uploading & Extracting Document...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-brand-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
            </div>
          )}

          <button
            type="button"
            onClick={handleUpload}
            disabled={!file || isUploading}
            className="w-full py-3 px-4 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-sm font-semibold shadow-lg shadow-brand-600/20 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {isUploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Processing Document Pipeline...</span>
              </>
            ) : (
              <>
                <UploadCloud className="w-4 h-4" />
                <span>Upload & Run Ingestion Pipeline</span>
              </>
            )}
          </button>
        </div>
      ) : (
        /* Extraction Success Result Card */
        <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-sm space-y-6 animate-in fade-in duration-200">
          <div className="flex items-center gap-3 text-emerald-600">
            <div className="w-10 h-10 rounded-full bg-emerald-50 border border-emerald-200 flex items-center justify-center">
              <Check className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Document Processed Successfully</h3>
              <p className="text-xs text-slate-500">Invoice record initialized in private storage.</p>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-slate-400 block text-[11px]">Invoice #</span>
              <span className="font-bold text-slate-800">{uploadResult.invoice.invoice_number}</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-slate-400 block text-[11px]">Pages Detected</span>
              <span className="font-bold text-slate-800">{uploadResult.page_count}</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-slate-400 block text-[11px]">Characters Extracted</span>
              <span className="font-bold text-slate-800">{uploadResult.char_count} chars</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-slate-400 block text-[11px]">Digital PDF</span>
              <span className={`font-bold ${uploadResult.is_digital ? 'text-emerald-600' : 'text-amber-600'}`}>
                {uploadResult.is_digital ? 'Yes (Native Text)' : 'Scanned / Image'}
              </span>
            </div>
          </div>

          {/* Extracted Text Snippet */}
          <div>
            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Extracted Text Preview
            </h4>
            <div className="p-4 bg-slate-900 text-slate-200 rounded-xl font-mono text-xs max-h-40 overflow-y-auto whitespace-pre-wrap leading-relaxed border border-slate-800">
              {uploadResult.extracted_text_snippet || 'No raw text detected. Document flagged for OCR.'}
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
            <button
              type="button"
              onClick={() => navigate(`/invoices/${uploadResult.invoice.id}`)}
              className="w-full sm:w-1/2 py-2.5 px-4 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-semibold shadow-sm transition-all flex items-center justify-center gap-2"
            >
              <Eye className="w-4 h-4" />
              <span>View Invoice Details</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setFile(null);
                setUploadResult(null);
              }}
              className="w-full sm:w-1/2 py-2.5 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition-all"
            >
              Upload Another Invoice
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
