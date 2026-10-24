"use client";

import React, { useState, useEffect } from "react";
import { Loader2, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface SaveButtonProps {
  onClick: () => Promise<void> | void;
  disabled?: boolean;
  label?: string;
  className?: string;
  fullWidth?: boolean;
}

export function SaveButton({
  onClick,
  disabled = false,
  label = "Save configuration",
  className = "",
  fullWidth = false,
}: SaveButtonProps) {
  const [saving, setSaving] = useState(false);
  const [justSaved, setJustSaved] = useState(false);

  const handleClick = async () => {
    if (disabled || saving) return;
    try {
      setSaving(true);
      await onClick();
      setJustSaved(true);
      setTimeout(() => setJustSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  };

  return (
    <button
      type="button"
      disabled={disabled || saving}
      onClick={handleClick}
      className={cn(
        "btn-primary h-11 px-6 text-[13px] font-semibold flex items-center justify-center gap-2 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none select-none",
        fullWidth && "w-full",
        className
      )}
    >
      {saving ? (
        <>
          <Loader2 className="w-4 h-4 animate-spin text-[var(--ink)]" />
          <span>Saving changes...</span>
        </>
      ) : justSaved ? (
        <>
          <Check className="w-4 h-4 text-[var(--ink)] stroke-[2.5]" />
          <span>Saved</span>
        </>
      ) : (
        <span>{label}</span>
      )}
    </button>
  );
}
