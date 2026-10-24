"use client";

import React from "react";

export interface SegmentOption<T extends string = string> {
  value: T;
  label: string;
  icon?: React.ReactNode;
}

interface SegmentedControlProps<T extends string = string> {
  options: SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
  className?: string;
  fullWidth?: boolean;
}

export function SegmentedControl<T extends string = string>({
  options,
  value,
  onChange,
  className = "",
  fullWidth = true,
}: SegmentedControlProps<T>) {
  return (
    <div
      className={`inline-flex p-1 rounded-xl bg-[var(--surface)] border border-[var(--border)] ${
        fullWidth ? "w-full" : ""
      } ${className}`}
      role="tablist"
    >
      {options.map((opt) => {
        const isActive = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(opt.value)}
            className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 text-[13px] font-medium rounded-lg transition-all duration-150 select-none ${
              isActive
                ? "bg-[var(--card)] text-[var(--text)] border border-[var(--border-strong)] shadow-sm"
                : "text-[var(--text-muted)] hover:text-[var(--text)] border border-transparent"
            }`}
          >
            {opt.icon && <span className="w-4 h-4 shrink-0">{opt.icon}</span>}
            <span>{opt.label}</span>
          </button>
        );
      })}
    </div>
  );
}
