"use client";

import React, { useState } from "react";
import { ChevronDown } from "lucide-react";
import { IconTile } from "@/components/ui/IconTile";
import { StatusBadge, StatusVariant } from "@/components/ui/StatusBadge";
import { Toggle } from "@/components/ui/Toggle";
import { cn } from "@/lib/utils";

interface FeatureRowProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  badge?: React.ReactNode;
  badgeLabel?: string;
  enabled?: boolean;
  onToggle?: (enabled: boolean) => void;
  children?: React.ReactNode;
  defaultExpanded?: boolean;
  className?: string;
}

export function FeatureRow({
  icon,
  title,
  description,
  badge,
  badgeLabel,
  enabled,
  onToggle,
  children,
  defaultExpanded = false,
  className = "",
}: FeatureRowProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const hasChildren = Boolean(children);
  const isToggleControlled = typeof enabled === "boolean" && typeof onToggle === "function";

  const renderBadge = () => {
    if (!badge) return null;
    if (React.isValidElement(badge)) return badge;
    if (typeof badge === "string") {
      return <StatusBadge status={badge as StatusVariant} label={badgeLabel} />;
    }
    return null;
  };

  return (
    <div
      className={cn(
        "rounded-2xl transition-all duration-200 border border-transparent",
        expanded && "bg-[var(--glass-bg)] border-[var(--glass-border)] shadow-md",
        className
      )}
    >
      {/* Row Header Item */}
      <div
        onClick={() => hasChildren && setExpanded(!expanded)}
        className={cn(
          "flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl cursor-pointer select-none group",
          !expanded && "hover:bg-[var(--glass-bg)]"
        )}
      >
        {/* Left: 44px Icon tile + title & description */}
        <div className="flex items-start sm:items-center gap-3.5 flex-1 min-w-0">
          <IconTile icon={icon} size="md" />
          <div className="min-w-0 flex-1">
            <div className="text-[14px] font-semibold text-[var(--ice-silver)] tracking-tight group-hover:text-white transition-colors truncate">
              {title}
            </div>
            <div className="text-[12px] text-[var(--text-muted)] truncate mt-0.5">
              {description}
            </div>
          </div>
        </div>

        {/* Right: Badge / Toggle & Accordion Chevron */}
        <div
          className="flex items-center gap-3 shrink-0 self-end sm:self-auto"
          onClick={(e) => isToggleControlled && e.stopPropagation()}
        >
          {renderBadge()}

          {isToggleControlled && (
            <Toggle
              checked={enabled}
              onChange={onToggle}
            />
          )}

          {hasChildren && (
            <div className="p-1 text-[var(--text-faint)] group-hover:text-[var(--ice-silver)] transition-colors">
              <ChevronDown
                className={cn(
                  "w-4 h-4 transition-transform duration-200",
                  expanded ? "rotate-180" : "rotate-0"
                )}
              />
            </div>
          )}
        </div>
      </div>

      {/* Expanded Inline Drawer (One surface level, separated by clean divider) */}
      {hasChildren && expanded && (
        <div className="px-5 pb-5 pt-2 border-t border-[var(--glass-border)] space-y-4 animate-in fade-in duration-150">
          {children}
        </div>
      )}
    </div>
  );
}
