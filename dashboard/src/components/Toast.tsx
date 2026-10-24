"use client";

import React, { useEffect } from "react";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";

interface ToastProps {
  type: "success" | "error" | "info" | "warning";
  message: string;
  onClose: () => void;
  duration?: number;
}

export function Toast({ type, message, onClose, duration = 3200 }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose();
    }, duration);
    return () => clearTimeout(timer);
  }, [onClose, duration]);

  const isSuccess = type === "success";
  const isError = type === "error";
  const isWarning = type === "warning";

  return (
    <div className="fixed top-5 right-5 z-50 flex items-center gap-3 bg-[var(--surface)] border border-[var(--border-strong)] px-4 py-3 rounded-xl shadow-2xl animate-in slide-in-from-top-3 fade-in duration-150 max-w-sm">
      {isSuccess && <CheckCircle2 className="w-4 h-4 text-[var(--success)] shrink-0" />}
      {isError && <AlertCircle className="w-4 h-4 text-[var(--error)] shrink-0" />}
      {isWarning && <AlertCircle className="w-4 h-4 text-[var(--warning)] shrink-0" />}
      {!isSuccess && !isError && !isWarning && <Info className="w-4 h-4 text-[var(--text-muted)] shrink-0" />}

      <span className="text-[13px] text-[var(--text)] leading-tight flex-1">
        {message}
      </span>

      <button
        onClick={onClose}
        className="text-[var(--text-faint)] hover:text-[var(--text)] p-1 transition-colors rounded-md cursor-pointer"
        aria-label="Dismiss notification"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
