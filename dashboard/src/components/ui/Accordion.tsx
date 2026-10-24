"use client";

import React, { useState } from "react";
import { ChevronDown } from "lucide-react";

interface AccordionProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
  className?: string;
}

export function Accordion({
  title,
  description,
  icon,
  defaultOpen = false,
  children,
  className = "",
}: AccordionProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div
      className={`rounded-2xl border border-[var(--glass-border)] glass-soft transition-all ${
        open ? "border-[var(--ice-silver)]/30 shadow-md" : ""
      } ${className}`}
    >
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-4 text-left cursor-pointer group select-none"
        aria-expanded={open}
      >
        <div className="flex items-center gap-2.5">
          {icon && <span className="text-[var(--hint)]">{icon}</span>}
          <div>
            <div className="text-[13px] font-medium text-[var(--ice-silver)] group-hover:text-white transition-colors">
              {title}
            </div>
            {description && (
              <div className="text-[12px] text-[var(--text-muted)] mt-0.5">
                {description}
              </div>
            )}
          </div>
        </div>

        <ChevronDown
          className={`w-4 h-4 text-[var(--text-faint)] group-hover:text-[var(--ice-silver)] transition-transform duration-200 ${
            open ? "rotate-180 text-[var(--ice-silver)]" : ""
          }`}
        />
      </button>

      {open && (
        <div className="px-4 pb-4 pt-1 border-t border-[var(--glass-border)] animate-in fade-in duration-200">
          {children}
        </div>
      )}
    </div>
  );
}
