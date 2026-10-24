"use client";

import React from "react";
import { Loader2, Check } from "lucide-react";

interface SaveBarProps {
  hasChanges: boolean;
  isSaving: boolean;
  onSave: () => void;
  onReset: () => void;
}

export function SaveBar({ hasChanges, isSaving, onSave, onReset }: SaveBarProps) {
  if (!hasChanges) return null;

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 w-full max-w-xl px-4 animate-in fade-in slide-in-from-bottom-5 duration-300">
      <div className="glass-strong border border-[var(--glass-border-strong)] shadow-2xl rounded-2xl px-5 py-3.5 flex items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <div className="w-2 h-2 rounded-full bg-[var(--hint)] animate-pulse" />
          <span className="text-xs font-mono tracking-wider uppercase text-[var(--ice-silver)] font-medium">
            Unsaved Modifications
          </span>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            disabled={isSaving}
            onClick={onReset}
            className="px-3.5 py-1.5 text-xs font-mono tracking-wider uppercase text-[var(--text-muted)] hover:text-[var(--ice-silver)] transition-colors disabled:opacity-40"
          >
            Discard
          </button>
          <button
            type="button"
            disabled={isSaving}
            onClick={onSave}
            className="flex items-center gap-2 bg-[var(--ice-silver)] text-[var(--ink)] font-bold text-xs font-mono tracking-wider uppercase px-4 py-2 rounded-xl transition-all shadow-md hover:opacity-90 disabled:opacity-50 cursor-pointer"
          >
            {isSaving ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Saving</span>
              </>
            ) : (
              <>
                <Check className="w-3.5 h-3.5 stroke-[2.5]" />
                <span>Save Changes</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
