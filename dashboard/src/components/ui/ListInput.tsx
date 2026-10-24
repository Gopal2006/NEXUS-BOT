"use client";

import React, { useState } from "react";
import { Plus, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ListInputProps {
  label: string;
  icon?: React.ReactNode;
  placeholder?: string;
  items: string[];
  onChange: (items: string[]) => void;
  helperText?: string;
  emptyText?: string;
  className?: string;
}

export function ListInput({
  label,
  icon,
  placeholder = "Add entry...",
  items,
  onChange,
  helperText,
  emptyText = "No items added yet.",
  className = "",
}: ListInputProps) {
  const [val, setVal] = useState("");

  const handleAdd = () => {
    const trimmed = val.trim();
    if (!trimmed) return;
    if (!items.includes(trimmed)) {
      onChange([...items, trimmed]);
    }
    setVal("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAdd();
    }
  };

  const handleRemove = (index: number) => {
    onChange(items.filter((_, i) => i !== index));
  };

  return (
    <div className={cn("space-y-2.5", className)}>
      <div className="flex items-center gap-2">
        {icon && <span className="text-[var(--text-muted)] text-sm">{icon}</span>}
        <label className="text-[13px] font-medium text-[var(--ice-silver)]">{label}</label>
      </div>

      {/* Input with inline "+" button */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <input
            type="text"
            value={val}
            onChange={(e) => setVal(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className="w-full input-base pr-10"
          />
          <button
            type="button"
            onClick={handleAdd}
            disabled={!val.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg text-[var(--ice-silver)] hover:bg-[var(--glass-bg)] disabled:opacity-30 disabled:hover:bg-transparent transition-colors cursor-pointer"
            title="Add item"
            aria-label="Add item"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </div>

      {helperText && (
        <p className="text-[12px] text-[var(--text-muted)]">{helperText}</p>
      )}

      {/* Chips Container */}
      {items.length === 0 ? (
        <div className="py-2.5 px-3 rounded-xl glass-soft text-xs text-[var(--text-faint)] italic border border-[var(--glass-border)]">
          {emptyText}
        </div>
      ) : (
        <div className="flex flex-wrap gap-2 pt-1">
          {items.map((item, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg glass-soft text-xs text-[var(--ice-silver)] border border-[var(--glass-border)]"
            >
              <span>{item}</span>
              <button
                type="button"
                onClick={() => handleRemove(idx)}
                className="text-[var(--text-faint)] hover:text-[var(--error)] p-0.5 rounded transition-colors"
                title="Remove"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
