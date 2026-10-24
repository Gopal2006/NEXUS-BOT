"use client";

import React from "react";

interface ColorPreset {
  name: string;
  hex: string;
}

const DEFAULT_PRESETS: ColorPreset[] = [
  { name: "Ice Silver", hex: "#DDE3E8" },
  { name: "Teal", hex: "#089790" },
  { name: "Muted Violet", hex: "#8E6B9A" },
  { name: "Discord Blurple", hex: "#5865F2" },
  { name: "Emerald", hex: "#34D399" },
  { name: "Gold", hex: "#FBBF24" },
  { name: "Ruby", hex: "#F87171" },
];

interface ColorSwatchProps {
  value: string;
  onChange: (hex: string) => void;
  presets?: ColorPreset[];
  className?: string;
}

export function ColorSwatch({
  value,
  onChange,
  presets = DEFAULT_PRESETS,
  className = "",
}: ColorSwatchProps) {
  const currentHex = value.toUpperCase();

  const handleHexChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let raw = e.target.value.replace(/[^0-9A-Fa-f]/g, "");
    if (raw.length > 6) raw = raw.slice(0, 6);
    onChange(`#${raw}`);
  };

  return (
    <div className={`flex flex-wrap items-center gap-2.5 ${className}`}>
      {/* 24px circular swatches */}
      <div className="flex items-center gap-2">
        {presets.map((p) => {
          const isSelected = currentHex === p.hex.toUpperCase();
          return (
            <button
              key={p.name}
              type="button"
              title={p.name}
              aria-label={`Select ${p.name} (${p.hex})`}
              onClick={() => onChange(p.hex)}
              className={`w-6 h-6 rounded-full transition-transform relative focus:outline-none ${
                isSelected
                  ? "scale-110 ring-2 ring-[var(--accent)] ring-offset-2 ring-offset-[var(--bg)]"
                  : "hover:scale-105 opacity-85 hover:opacity-100"
              }`}
              style={{ backgroundColor: p.hex }}
            />
          );
        })}
      </div>

      {/* Small custom hex input */}
      <div className="flex items-center gap-1.5 h-8 bg-[var(--card)] border border-[var(--border)] rounded-md px-2 text-xs focus-within:border-[var(--accent)] transition-colors">
        <span className="text-[var(--text-faint)] font-mono select-none">#</span>
        <input
          type="text"
          value={value.replace("#", "")}
          onChange={handleHexChange}
          placeholder="DDE3E8"
          maxLength={6}
          className="w-16 bg-transparent text-[var(--text)] font-mono text-xs focus:outline-none uppercase"
        />
      </div>
    </div>
  );
}
