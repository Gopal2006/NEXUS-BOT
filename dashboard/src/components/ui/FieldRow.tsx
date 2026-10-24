import React from "react";

interface FieldRowProps {
  label: string;
  helperText?: string;
  required?: boolean;
  error?: string;
  children: React.ReactNode;
  className?: string;
}

export function FieldRow({
  label,
  helperText,
  required = false,
  error,
  children,
  className = "",
}: FieldRowProps) {
  return (
    <div className={`space-y-2 ${className}`}>
      <label className="text-[13px] font-medium text-[var(--text)] flex items-center justify-between">
        <span>
          {label} {required && <span className="text-[var(--error)]">*</span>}
        </span>
      </label>

      <div>{children}</div>

      {error ? (
        <p className="text-[12px] text-[var(--error)] leading-normal">{error}</p>
      ) : helperText ? (
        <p className="text-[12px] text-[var(--text-muted)] leading-normal">{helperText}</p>
      ) : null}
    </div>
  );
}
