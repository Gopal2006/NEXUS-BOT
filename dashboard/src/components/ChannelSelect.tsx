"use client";

import React from "react";
import { ChevronDown } from "lucide-react";
import { stripEmojis } from "@/lib/utils";

export interface Channel {
  id: string;
  name: string;
  type: string;
  category_id?: string | null;
}

interface ChannelSelectProps {
  label?: string;
  description?: string;
  channels: Channel[];
  value: string | null;
  onChange: (value: string | null) => void;
  filterType?: "text" | "voice" | "category" | "all";
  placeholder?: string;
  disabled?: boolean;
}

export function ChannelSelect({
  label,
  description,
  channels,
  value,
  onChange,
  filterType = "text",
  placeholder = "Select channel",
  disabled = false,
}: ChannelSelectProps) {
  const filtered =
    filterType === "all"
      ? channels
      : channels.filter((c) => (filterType ? c.type === filterType : true));

  return (
    <div className="space-y-1.5">
      {label && (
        <label className="text-[13px] font-medium text-[var(--ice-silver)] block">
          {label}
        </label>
      )}
      {description && (
        <p className="text-[12px] text-[var(--text-muted)]">{description}</p>
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
          {filtered.map((ch) => {
            const cleanName = stripEmojis(ch.name);
            const prefix = ch.type === "voice" ? "VOICE: " : ch.type === "category" ? "CATEGORY: " : "# ";

            return (
              <option key={ch.id} value={ch.id} className="bg-[var(--glass-bg-strong)] text-[var(--ice-silver)]">
                {prefix}{cleanName}
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
