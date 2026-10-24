"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface ToggleProps {
  label?: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

export function Toggle({
  label,
  description,
  checked,
  onChange,
  disabled,
}: ToggleProps) {
  return (
    <div className={cn("flex items-center justify-between", label ? "py-1.5" : "")}>
      {label && (
        <div className="pr-4 select-none">
          <label className="text-[13px] font-medium text-[var(--ice-silver)] block cursor-pointer">
            {label}
          </label>
          {description && (
            <p className="text-[12px] text-[var(--text-muted)] mt-0.5">{description}</p>
          )}
        </div>
      )}

      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={cn(
          "relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border border-transparent transition-all duration-300 ease-in-out focus:outline-none focus:ring-2 focus:ring-[var(--ice-silver)]/50 focus:ring-offset-2 focus:ring-offset-[var(--bg-deep)]",
          checked
            ? "bg-[var(--ice-silver)] shadow-[0_0_12px_rgba(221,227,232,0.35)]"
            : "glass-soft border border-[var(--glass-border)]",
          disabled && "opacity-40 cursor-not-allowed"
        )}
      >
        <span
          className={cn(
            "pointer-events-none inline-block h-5 w-5 transform rounded-full shadow-md transition-transform duration-300 ease-in-out",
            checked
              ? "translate-x-5 bg-[var(--ink)]"
              : "translate-x-0.5 bg-[var(--ice-silver)]/60"
          )}
        />
      </button>
    </div>
  );
}
