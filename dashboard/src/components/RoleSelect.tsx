"use client";

import React from "react";
import { ChevronDown } from "lucide-react";
import { stripEmojis } from "@/lib/utils";

export interface Role {
  id: string;
  name: string;
  color: string;
  position: number;
  manageable?: boolean;
}

interface RoleSelectProps {
  label?: string;
  description?: string;
  roles: Role[];
  value: string | null;
  onChange: (value: string | null) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function RoleSelect({
  label,
  description,
  roles,
  value,
  onChange,
  placeholder = "Select a role...",
  disabled,
}: RoleSelectProps) {
  return (
    <div className={label ? "space-y-1.5" : ""}>
      {label && (
        <label className="text-[13px] font-medium text-[var(--ice-silver)] block">
          {label}
        </label>
      )}
      {description && (
        <p className="text-[12px] text-[var(--text-muted)] mb-1.5">{description}</p>
      )}
      <div className="relative">
        <select
          value={value || ""}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value ? e.target.value : null)}
          className="w-full h-11 input-base pr-8 text-[13px] appearance-none cursor-pointer disabled:opacity-40"
        >
          <option value="" className="bg-[var(--glass-bg-strong)] text-[var(--text-muted)]">
            -- {placeholder} --
          </option>
          {roles.map((r) => {
            const cleanName = stripEmojis(r.name);
            return (
              <option key={r.id} value={r.id} className="bg-[var(--glass-bg-strong)] text-[var(--ice-silver)]">
                @{cleanName} {!r.manageable ? "(Higher Role)" : ""}
              </option>
            );
          })}
        </select>
        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-[var(--text-muted)]">
          <ChevronDown className="w-4 h-4" />
        </div>
      </div>
    </div>
  );
}
