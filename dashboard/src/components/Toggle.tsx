"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface ToggleProps {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  statusMode?: boolean; // If true, uses --success when active
}

export function Toggle({
  label,
  description,
  checked,
  onChange,
  disabled,
  statusMode = false,
}: ToggleProps) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <div className="pr-4 select-none">
        <label className="text-[13px] font-medium text-[var(--text)] block cursor-pointer">
          {label}
        </label>
        {description && (
          <p className="text-[12px] text-[var(--text-muted)] mt-0.5">{description}</p>
        )}
      </div>

      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={cn(
          "relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 focus:ring-offset-2 focus:ring-offset-[var(--bg)]",
          checked
            ? statusMode
              ? "bg-[var(--success)]"
              : "bg-[var(--accent)]"
            : "bg-[var(--border-strong)]",
          disabled && "opacity-40 cursor-not-allowed"
        )}
      >
        <span
          className={cn(
            "pointer-events-none inline-block h-5 w-5 transform rounded-full shadow transition duration-200 ease-in-out",
            checked
              ? "translate-x-5 bg-[var(--accent-ink)]"
              : "translate-x-0 bg-[var(--text)]"
          )}
        />
      </button>
    </div>
  );
}
