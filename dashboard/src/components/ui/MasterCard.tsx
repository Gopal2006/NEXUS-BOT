"use client";

import React from "react";
import { GlassCard } from "@/components/ui/GlassCard";
import { Toggle } from "@/components/ui/Toggle";
import { cn } from "@/lib/utils";

interface MasterCardProps {
  label?: string;
  title: string;
  description?: string;
  enabled?: boolean;
  onToggle?: (enabled: boolean) => void;
  children: React.ReactNode;
  action?: React.ReactNode;
  badge?: React.ReactNode;
  className?: string;
}

export function MasterCard({
  label = "MASTER CONTROL",
  title,
  description,
  enabled = true,
  onToggle,
  children,
  action,
  badge,
  className = "",
}: MasterCardProps) {
  const isToggleControlled = typeof onToggle === "function";
  const isMasterOff = isToggleControlled && !enabled;

  return (
    <GlassCard variant="base" sheen={false} className={cn("space-y-6", className)}>
      {/* Master Card Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--glass-border)]">
        <div>
          <div className="text-[10px] font-mono tracking-[0.2em] uppercase text-[var(--hint)] font-semibold mb-1">
            {label}
          </div>
          <h2 className="text-xl font-bold tracking-tight text-[var(--ice-silver)]">
            {title}
          </h2>
          {description && (
            <p className="text-[13px] text-[var(--text-muted)] mt-1 max-w-2xl leading-relaxed">
              {description}
            </p>
          )}
        </div>

        {/* Master Control Toggle, Badge or Action */}
        <div className="shrink-0 flex items-center gap-3">
          {badge}
          {action}
          {isToggleControlled && (
            <div className="flex items-center gap-2 pl-2">
              <span className="text-[11px] font-mono tracking-wider uppercase text-[var(--text-faint)]">
                {enabled ? "Active" : "Disabled"}
              </span>
              <Toggle
                checked={enabled}
                onChange={onToggle}
              />
            </div>
          )}
        </div>
      </div>

      {/* Child Rows Area: Fades to 40% and non-interactive when master is off */}
      <div
        className={cn(
          "space-y-2 transition-opacity duration-200",
          isMasterOff && "opacity-40 pointer-events-none select-none"
        )}
      >
        {children}
      </div>
    </GlassCard>
  );
}
