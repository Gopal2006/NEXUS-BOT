"use client";

import React from "react";
import { Loader2 } from "lucide-react";

interface StickySaveBarProps {
  show?: boolean;
  hasChanges?: boolean;
  isSaving?: boolean;
  loading?: boolean;
  onSave: () => void;
  onDiscard?: () => void;
  saveLabel?: string;
  discardLabel?: string;
  message?: string;
}

export function StickySaveBar({
  show,
  hasChanges,
  isSaving,
  loading,
  onSave,
  onDiscard,
  saveLabel = "Save changes",
  discardLabel = "Discard",
  message = "Careful — you have unsaved changes",
}: StickySaveBarProps) {
  const isVisible = show ?? hasChanges ?? false;
  const inProgress = isSaving ?? loading ?? false;

  if (!isVisible) return null;

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 w-full max-w-xl px-4 animate-in fade-in slide-in-from-bottom-5 duration-200">
      <div className="glass-strong border border-[var(--glass-border-strong)] shadow-2xl rounded-2xl px-5 py-3.5 flex items-center justify-between gap-4">
        <div className="flex items-center gap-2.5 text-xs text-[var(--ice-silver)] font-sans">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--hint)] animate-pulse" />
          <span className="font-medium">{message}</span>
        </div>

        <div className="flex items-center gap-2.5">
          {onDiscard && (
            <button
              type="button"
              disabled={inProgress}
              onClick={onDiscard}
              className="px-3.5 py-1.5 rounded-xl glass-soft border border-[var(--glass-border)] text-xs font-mono uppercase tracking-wider text-[var(--text-muted)] hover:text-[var(--ice-silver)] transition-colors cursor-pointer disabled:opacity-40"
            >
              {discardLabel}
            </button>
          )}

          <button
            type="button"
            disabled={inProgress}
            onClick={onSave}
            className="px-4 py-1.5 rounded-xl bg-[var(--ice-silver)] text-[var(--ink)] font-mono text-xs font-bold uppercase tracking-wider hover:opacity-90 transition-all flex items-center gap-1.5 shadow-md cursor-pointer disabled:opacity-40"
          >
            {inProgress && <Loader2 className="w-3.5 h-3.5 animate-spin text-[var(--ink)]" />}
            <span>{inProgress ? "Saving..." : saveLabel}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
