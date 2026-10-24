"use client";

import React from "react";
import { Toggle } from "@/components/Toggle";

interface SectionProps {
  title: string;
  description?: string;
  enabled?: boolean;
  onToggle?: (enabled: boolean) => void;
  toggleLabel?: string;
  children: React.ReactNode;
  className?: string;
}

export function Section({
  title,
  description,
  enabled,
  onToggle,
  toggleLabel,
  children,
  className = "",
}: SectionProps) {
  const isControlled = typeof enabled === "boolean" && typeof onToggle === "function";
  const isDisabled = isControlled && !enabled;

  return (
    <div
      className={`pt-8 pb-8 border-b border-[var(--border)] last:border-b-0 first:pt-0 ${className}`}
    >
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column (~30% / 4 cols) */}
        <div className="lg:col-span-4 space-y-3">
          <div>
            <h3 className="text-base font-semibold text-[var(--text)] tracking-tight">
              {title}
            </h3>
            {description && (
              <p className="text-[13px] text-[var(--text-muted)] mt-1 leading-relaxed">
                {description}
              </p>
            )}
          </div>

          {/* Optional Enable/Disable toggle for this section */}
          {isControlled && (
            <div className="pt-1">
              <Toggle
                label={toggleLabel || (enabled ? "Enabled" : "Disabled")}
                checked={enabled}
                onChange={onToggle}
              />
            </div>
          )}
        </div>

        {/* Right Column (~70% / 8 cols) */}
        <div
          className={`lg:col-span-8 space-y-5 transition-opacity duration-200 ${
            isDisabled ? "opacity-40 pointer-events-none select-none" : "opacity-100"
          }`}
        >
          {children}
        </div>
      </div>
    </div>
  );
}
