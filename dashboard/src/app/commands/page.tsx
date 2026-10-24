"use client";

import React, { useState, useMemo, useEffect, useRef, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Search,
  Copy,
  Check,
  Terminal,
  ArrowLeft,
  X,
  ExternalLink,
  Shield,
  Layers,
  ChevronRight,
  Info,
  Sparkles,
} from "lucide-react";
import { COMMANDS_DATABASE, CommandItem } from "@/lib/commandsData";
import { TierDot } from "@/components/ui/TierDot";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { CountUp } from "@/components/ui/CountUp";
import { BackgroundAurora } from "@/components/BackgroundAurora";
import { FloatingTopBar } from "@/components/FloatingTopBar";
import { cn } from "@/lib/utils";

function CommandsDirectoryContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // URL sync state
  const initialQ = searchParams.get("q") || "";
  const initialTier = searchParams.get("tier") || "All";
  const initialCmdId = searchParams.get("cmd") || "setupbot";

  const [searchTerm, setSearchTerm] = useState(initialQ);
  const [selectedTier, setSelectedTier] = useState(initialTier);
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [selectedCommandId, setSelectedCommandId] = useState<string>(initialCmdId);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [mobileDetailOpen, setMobileDetailOpen] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);

  const searchInputRef = useRef<HTMLInputElement>(null);
  const listContainerRef = useRef<HTMLDivElement>(null);
  const lettersRef = useRef<(HTMLSpanElement | null)[]>([]);

  // Mouse velocity tracking for title letters
  const mouseState = useRef({
    lastX: 0,
    lastY: 0,
    lastTime: 0,
    velocity: 0,
    smoothedVelocity: 0,
    dirX: 0,
    idleTimeout: 0,
  });

  useEffect(() => {
    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(motionQuery.matches);
    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    motionQuery.addEventListener("change", handler);

    if (motionQuery.matches) return;

    let rafId: number;
    const onMouseMove = (e: MouseEvent) => {
      const now = performance.now();
      const dt = Math.max(10, now - mouseState.current.lastTime);
      const dx = e.clientX - mouseState.current.lastX;
      const dy = e.clientY - mouseState.current.lastY;
      const dist = Math.sqrt(dx * dx + dy * dy);

      mouseState.current.velocity = dist / dt;
      mouseState.current.dirX = dx !== 0 ? Math.sign(dx) : 0;
      mouseState.current.lastX = e.clientX;
      mouseState.current.lastY = e.clientY;
      mouseState.current.lastTime = now;
      mouseState.current.idleTimeout = now + 90;
    };

    window.addEventListener("mousemove", onMouseMove, { passive: true });

    const updateLetterBlur = (now: number) => {
      if (now > mouseState.current.idleTimeout) {
        mouseState.current.velocity = 0;
      }
      mouseState.current.smoothedVelocity +=
        (mouseState.current.velocity - mouseState.current.smoothedVelocity) * 0.18;

      const v = mouseState.current.smoothedVelocity;
      const blurPx = Math.min(8, v * 3.2);
      const dir = mouseState.current.dirX;

      lettersRef.current.forEach((el, idx) => {
        if (!el) return;
        if (v < 0.02) {
          el.style.filter = "none";
          el.style.transform = "none";
        } else {
          const offset = dir * Math.min(10, v * 4) * (1 + (idx - 3) * 0.1);
          el.style.filter = `blur(${blurPx.toFixed(2)}px)`;
          el.style.transform = `translateX(${offset.toFixed(2)}px)`;
        }
      });

      rafId = requestAnimationFrame(updateLetterBlur);
    };

    rafId = requestAnimationFrame(updateLetterBlur);

    return () => {
      motionQuery.removeEventListener("change", handler);
      window.removeEventListener("mousemove", onMouseMove);
      cancelAnimationFrame(rafId);
    };
  }, []);

  // Categories list with counts
  const categoriesWithCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    COMMANDS_DATABASE.forEach((c) => {
      counts[c.category] = (counts[c.category] || 0) + 1;
    });

    const list = Object.entries(counts).map(([name, count]) => ({
      name,
      count,
    }));

    return [{ name: "All", count: COMMANDS_DATABASE.length }, ...list];
  }, []);

  // Filter commands
  const filteredCommands = useMemo(() => {
    const q = searchTerm.toLowerCase().trim();
    return COMMANDS_DATABASE.filter((cmd) => {
      const matchesSearch =
        !q ||
        cmd.name.toLowerCase().includes(q) ||
        cmd.syntax.toLowerCase().includes(q) ||
        cmd.description.toLowerCase().includes(q) ||
        (cmd.aliases && cmd.aliases.some((a) => a.toLowerCase().includes(q)));

      const matchesTier =
        selectedTier === "All" ||
        cmd.tier.toLowerCase() === selectedTier.toLowerCase();

      const matchesCat =
        selectedCategory === "All" || cmd.category === selectedCategory;

      return matchesSearch && matchesTier && matchesCat;
    });
  }, [searchTerm, selectedTier, selectedCategory]);

  // Group commands by category for center list
  const groupedCommands = useMemo(() => {
    const groups: Record<string, CommandItem[]> = {};
    filteredCommands.forEach((cmd) => {
      if (!groups[cmd.category]) groups[cmd.category] = [];
      groups[cmd.category].push(cmd);
    });
    return groups;
  }, [filteredCommands]);

  // Selected command item
  const selectedCommand = useMemo(() => {
    const found = COMMANDS_DATABASE.find((c) => c.id === selectedCommandId);
    return found || filteredCommands[0] || COMMANDS_DATABASE[0];
  }, [selectedCommandId, filteredCommands]);

  // Sync state to URL
  useEffect(() => {
    const paramsObj = new URLSearchParams();
    if (searchTerm) paramsObj.set("q", searchTerm);
    if (selectedTier !== "All") paramsObj.set("tier", selectedTier);
    if (selectedCommand?.id) paramsObj.set("cmd", selectedCommand.id);

    const newUrl = `${window.location.pathname}?${paramsObj.toString()}`;
    window.history.replaceState(null, "", newUrl);
  }, [searchTerm, selectedTier, selectedCommand]);

  // Keyboard Navigation: Up/Down, Enter, Esc, C, /
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't intercept if focused in search input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        if (e.key === "Escape") {
          searchInputRef.current?.blur();
        }
        return;
      }

      if (e.key === "/") {
        e.preventDefault();
        searchInputRef.current?.focus();
        return;
      }

      if (e.key === "c" || e.key === "C") {
        if (selectedCommand) {
          e.preventDefault();
          copyText(selectedCommand.syntax, selectedCommand.id);
        }
        return;
      }

      if (e.key === "Escape") {
        setMobileDetailOpen(false);
        return;
      }

      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const currentIndex = filteredCommands.findIndex((c) => c.id === selectedCommand?.id);
        if (currentIndex === -1) return;

        const nextIndex =
          e.key === "ArrowDown"
            ? (currentIndex + 1) % filteredCommands.length
            : (currentIndex - 1 + filteredCommands.length) % filteredCommands.length;

        const nextCmd = filteredCommands[nextIndex];
        if (nextCmd) {
          setSelectedCommandId(nextCmd.id);
        }
      }

      if (e.key === "Enter") {
        if (selectedCommand) {
          setMobileDetailOpen(true);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [filteredCommands, selectedCommand]);

  const copyText = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  // Related commands in same category
  const relatedCommands = useMemo(() => {
    if (!selectedCommand) return [];
    return COMMANDS_DATABASE.filter(
      (c) => c.category === selectedCommand.category && c.id !== selectedCommand.id
    ).slice(0, 3);
  }, [selectedCommand]);

  // Highlight syntax tokens: <required> in --hint (#8E6B9A), [optional] in muted
  const renderHighlightedSyntax = (syntax: string) => {
    const parts = syntax.split(/(<[^>]+>|\[[^\]]+\])/g);
    return parts.map((part, i) => {
      if (part.startsWith("<") && part.endsWith(">")) {
        return (
          <span key={i} className="text-[var(--hint)] font-semibold">
            {part}
          </span>
        );
      }
      if (part.startsWith("[") && part.endsWith("]")) {
        return (
          <span key={i} className="text-[var(--text-faint)]">
            {part}
          </span>
        );
      }
      return <span key={i}>{part}</span>;
    });
  };

  const titleChars = ["C", "o", "m", "m", "a", "n", "d", "s"];

  return (
    <div className="min-h-screen bg-[var(--bg-deep)] text-[var(--ice-silver)] relative pb-20 selection:bg-[var(--ice-silver)]/20 selection:text-white">
      <BackgroundAurora />

      <div className="relative z-10 max-w-[1440px] mx-auto px-4 sm:px-8">
        <FloatingTopBar />

        {/* Header Hero Section */}
        <div className="pt-8 pb-10 border-b border-[var(--glass-border)]">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-6">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Link
                  href="/dashboard"
                  className="inline-flex items-center gap-1.5 text-xs font-mono tracking-wider uppercase text-[var(--text-faint)] hover:text-[var(--ice-silver)] transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Dashboard</span>
                </Link>
              </div>

              {/* Huge Display Title with Velocity Motion Blur on Letters */}
              <h1 className="font-display font-black text-6xl sm:text-7xl md:text-8xl tracking-tight text-[var(--ice-silver)] leading-none select-none flex items-center">
                {titleChars.map((char, i) => (
                  <span
                    key={i}
                    ref={(el) => {
                      lettersRef.current[i] = el;
                    }}
                    className="inline-block transition-transform duration-75 will-change-transform"
                  >
                    {char}
                  </span>
                ))}
              </h1>

              <p className="text-[13px] sm:text-sm text-[var(--text-muted)] mt-3 max-w-xl leading-relaxed">
                Explore parameter schemas, permissions, and execution syntax for NEXUS.
              </p>
            </div>

            {/* Live Count-Up Indicator */}
            <div className="shrink-0 flex items-center gap-3">
              <div className="glass-soft px-4 py-2 rounded-xl text-right border border-[var(--glass-border)]">
                <div className="text-[10px] font-mono tracking-[0.18em] uppercase text-[var(--text-faint)]">
                  ACTIVE COMMANDS
                </div>
                <div className="font-display font-bold text-2xl text-[var(--ice-silver)]">
                  <CountUp end={filteredCommands.length} />
                  <span className="text-xs text-[var(--text-faint)] font-mono font-normal ml-1">
                    / {COMMANDS_DATABASE.length}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Search Bar + Access Tier Segmented Control */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-4 mt-8 items-center">
            {/* Search Input Bar (8 cols) */}
            <div className="md:col-span-7 lg:col-span-8 relative">
              <Search className="w-4 h-4 text-[var(--text-faint)] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                ref={searchInputRef}
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search commands by name, syntax, description, or keyword..."
                className="w-full h-11 input-base pl-10 pr-10 text-[13px]"
              />
              {searchTerm ? (
                <button
                  type="button"
                  onClick={() => setSearchTerm("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-[var(--text-faint)] hover:text-[var(--ice-silver)] transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              ) : (
                <kbd className="hidden sm:inline-block absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono text-[var(--text-faint)] bg-black/20 border border-[var(--glass-border)] px-1.5 py-0.5 rounded">
                  /
                </kbd>
              )}
            </div>

            {/* Access Tier Segmented Control (4 cols) */}
            <div className="md:col-span-5 lg:col-span-4">
              <SegmentedControl
                options={[
                  { value: "All", label: "All" },
                  { value: "public", label: "Public" },
                  { value: "staff", label: "Staff" },
                  { value: "owner", label: "Owner" },
                ]}
                value={selectedTier}
                onChange={setSelectedTier}
              />
            </div>
          </div>
        </div>

        {/* Main Two-Pane Command Palette Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start pt-8">
          {/* LEFT RAIL (3 cols / ~240px, sticky): Categories with counts */}
          <div className="lg:col-span-3 space-y-2 lg:sticky lg:top-24">
            <div className="text-[10px] font-mono tracking-[0.2em] uppercase text-[var(--text-faint)] px-2 mb-2 font-semibold">
              CATEGORIES
            </div>

            {/* Category selection buttons with command counts */}
            <div className="flex lg:flex-col gap-1.5 overflow-x-auto pb-2 lg:pb-0 scrollbar-none">
              {categoriesWithCounts.map((cat) => {
                const isActive = selectedCategory === cat.name;

                return (
                  <button
                    key={cat.name}
                    type="button"
                    onClick={() => setSelectedCategory(cat.name)}
                    className={cn(
                      "w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-[13px] font-medium transition-all cursor-pointer select-none text-left shrink-0 lg:shrink",
                      isActive
                        ? "glass-soft text-[var(--ice-silver)] border border-[var(--glass-border-strong)] font-semibold shadow-sm"
                        : "text-[var(--text-muted)] hover:text-[var(--ice-silver)] hover:bg-[var(--tint)] border border-transparent"
                    )}
                  >
                    <span>{cat.name}</span>
                    <span
                      className={cn(
                        "text-[11px] font-mono px-2 py-0.5 rounded-full ml-2",
                        isActive
                          ? "bg-[var(--ice-silver)] text-[var(--ink)] font-bold"
                          : "text-[var(--text-faint)] bg-black/20"
                      )}
                    >
                      {cat.count}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Quick Keyboard Hint Box */}
            <div className="hidden lg:block pt-6 border-t border-[var(--glass-border)] text-[11px] font-mono text-[var(--text-faint)] space-y-1.5 px-2">
              <div className="flex items-center justify-between">
                <span>Navigate</span>
                <span className="text-[var(--text-muted)]">↑ ↓</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Copy syntax</span>
                <span className="text-[var(--text-muted)]">C</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Search</span>
                <span className="text-[var(--text-muted)]">/</span>
              </div>
            </div>
          </div>

          {/* CENTER LIST (5 cols): Compact ~56px rows grouped by category */}
          <div ref={listContainerRef} className="lg:col-span-5 space-y-8">
            {filteredCommands.length === 0 ? (
              <div className="text-center py-16 glass rounded-2xl p-8 border border-[var(--glass-border)]">
                <Info className="w-8 h-8 text-[var(--text-faint)] mx-auto mb-3" />
                <h3 className="text-base font-semibold text-[var(--ice-silver)] mb-1">
                  No commands found
                </h3>
                <p className="text-xs text-[var(--text-muted)] mb-4">
                  No commands match your filter query.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setSearchTerm("");
                    setSelectedTier("All");
                    setSelectedCategory("All");
                  }}
                  className="btn-secondary px-4 py-2 text-xs"
                >
                  Clear filters
                </button>
              </div>
            ) : (
              Object.entries(groupedCommands).map(([categoryName, cmds]) => (
                <div key={categoryName} className="space-y-2">
                  {/* Category group header */}
                  <div className="flex items-center justify-between px-2 py-1 sticky top-20 bg-[var(--bg-deep)]/90 backdrop-blur-md z-10 border-b border-[var(--glass-border)]">
                    <span className="text-[11px] font-mono tracking-[0.18em] uppercase text-[var(--hint)] font-semibold">
                      {categoryName}
                    </span>
                    <span className="text-[11px] font-mono text-[var(--text-faint)]">
                      {cmds.length}
                    </span>
                  </div>

                  {/* Compact command rows (~56px high) */}
                  <div className="space-y-1">
                    {cmds.map((cmd) => {
                      const isSelected = selectedCommand?.id === cmd.id;
                      const hasPrefixOnly = !cmd.type.includes("slash");

                      return (
                        <div
                          key={cmd.id}
                          onClick={() => {
                            setSelectedCommandId(cmd.id);
                            setMobileDetailOpen(true);
                          }}
                          className={cn(
                            "h-14 px-3.5 rounded-xl flex items-center justify-between gap-3 cursor-pointer transition-all border group select-none",
                            isSelected
                              ? "glass-soft text-[var(--ice-silver)] border-[var(--glass-border-strong)] shadow-md"
                              : "hover:bg-[var(--tint)] border-transparent text-[var(--text-muted)] hover:text-[var(--ice-silver)]"
                          )}
                        >
                          {/* Command Name + Truncated Description */}
                          <div className="flex items-center gap-3 min-w-0 flex-1">
                            <span className="font-mono text-[14px] font-semibold text-[var(--ice-silver)] shrink-0 group-hover:text-white">
                              {cmd.name}
                            </span>

                            {hasPrefixOnly && (
                              <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-[var(--tint)] text-[var(--text-faint)] border border-[var(--glass-border)]">
                                prefix
                              </span>
                            )}

                            <span className="text-xs text-[var(--text-faint)] truncate hidden sm:inline">
                              {cmd.description}
                            </span>
                          </div>

                          {/* Right: Tier dot + Hover-only copy icon */}
                          <div className="flex items-center gap-3 shrink-0">
                            <TierDot tier={cmd.tier} />

                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                copyText(cmd.syntax, cmd.id);
                              }}
                              className="p-1.5 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-[var(--glass-bg)] text-[var(--text-faint)] hover:text-[var(--ice-silver)] transition-all"
                              title="Copy command syntax"
                            >
                              {copiedId === cmd.id ? (
                                <Check className="w-3.5 h-3.5 text-[var(--success)]" />
                              ) : (
                                <Copy className="w-3.5 h-3.5" />
                              )}
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* RIGHT DETAIL PANEL (4 cols / ~420px, sticky glass-strong): Desktop view */}
          <div className="hidden lg:block lg:col-span-4 lg:sticky lg:top-24">
            {selectedCommand ? (
              <div className="glass-strong rounded-2xl p-6 border border-[var(--glass-border-strong)] shadow-2xl space-y-6 animate-in fade-in slide-in-from-right-2 duration-150">
                {/* Detail Header */}
                <div className="border-b border-[var(--glass-border)] pb-4">
                  <div className="flex items-center justify-between text-xs text-[var(--text-faint)] mb-2">
                    <span className="font-mono tracking-wider uppercase text-[var(--hint)]">
                      {selectedCommand.category}
                    </span>
                    <TierDot tier={selectedCommand.tier} />
                  </div>

                  <h2 className="font-mono font-bold text-2xl text-[var(--ice-silver)] tracking-tight">
                    {selectedCommand.name}
                  </h2>

                  <p className="text-[13px] text-[var(--text-muted)] mt-2 leading-relaxed">
                    {selectedCommand.description}
                  </p>
                </div>

                {/* SYNTAX BLOCK (Terminal-style with token highlighting & copy button) */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-[11px] font-mono uppercase text-[var(--text-faint)]">
                    <span>SYNTAX SPECIFICATION</span>
                    {copiedId === selectedCommand.id && (
                      <span className="text-[var(--success)] font-sans text-xs">Copied</span>
                    )}
                  </div>

                  <div className="relative group bg-black/40 border border-[var(--glass-border)] rounded-xl p-3 font-mono text-xs text-[var(--ice-silver)] overflow-x-auto">
                    <code>{renderHighlightedSyntax(selectedCommand.syntax)}</code>

                    <button
                      type="button"
                      onClick={() => copyText(selectedCommand.syntax, selectedCommand.id)}
                      className="absolute right-2.5 top-2.5 p-1.5 rounded-lg glass-soft text-[var(--text-faint)] hover:text-[var(--ice-silver)] transition-colors cursor-pointer"
                      title="Copy syntax"
                    >
                      {copiedId === selectedCommand.id ? (
                        <Check className="w-3.5 h-3.5 text-[var(--success)]" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>

                {/* EXAMPLE INVOCATION BLOCK */}
                <div className="space-y-1.5">
                  <div className="text-[11px] font-mono uppercase text-[var(--text-faint)]">
                    EXAMPLE INVOCATION
                  </div>
                  <div className="relative group bg-black/40 border border-[var(--glass-border)] rounded-xl p-3 font-mono text-xs text-[var(--ice-silver)]">
                    <code>{selectedCommand.example}</code>
                    <button
                      type="button"
                      onClick={() => copyText(selectedCommand.example, `${selectedCommand.id}-ex`)}
                      className="absolute right-2.5 top-2.5 p-1.5 rounded-lg glass-soft text-[var(--text-faint)] hover:text-[var(--ice-silver)] transition-colors cursor-pointer"
                      title="Copy example"
                    >
                      {copiedId === `${selectedCommand.id}-ex` ? (
                        <Check className="w-3.5 h-3.5 text-[var(--success)]" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>

                {/* PARAMETERS TABLE (if any parameters) */}
                {selectedCommand.parameters && selectedCommand.parameters.length > 0 && (
                  <div className="space-y-2">
                    <div className="text-[11px] font-mono uppercase text-[var(--text-faint)]">
                      PARAMETERS ({selectedCommand.parameters.length})
                    </div>
                    <div className="rounded-xl border border-[var(--glass-border)] overflow-hidden text-xs">
                      <table className="w-full text-left border-collapse">
                        <thead className="bg-black/30 border-b border-[var(--glass-border)] text-[var(--text-faint)] font-mono text-[10px] uppercase">
                          <tr>
                            <th className="p-2">Name</th>
                            <th className="p-2">Type</th>
                            <th className="p-2">Description</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[var(--glass-border)]">
                          {selectedCommand.parameters.map((param, i) => (
                            <tr key={i} className="hover:bg-[var(--tint)]">
                              <td className="p-2 font-mono text-[var(--ice-silver)]">
                                {param.name}
                              </td>
                              <td className="p-2">
                                <span
                                  className={cn(
                                    "px-1.5 py-0.5 rounded text-[10px] font-mono uppercase",
                                    param.required
                                      ? "bg-[var(--error)]/10 text-[var(--error)] border border-[var(--error)]/20"
                                      : "bg-[var(--tint)] text-[var(--text-faint)]"
                                  )}
                                >
                                  {param.required ? "Req" : "Opt"}
                                </span>
                              </td>
                              <td className="p-2 text-[var(--text-muted)] text-[11px]">
                                {param.desc}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* EXPECTED DISCORD RESPONSE */}
                {selectedCommand.expectedResponse && (
                  <div className="space-y-1">
                    <div className="text-[11px] font-mono uppercase text-[var(--text-faint)]">
                      RESPONSE BEHAVIOR
                    </div>
                    <p className="text-xs text-[var(--text-muted)] leading-relaxed italic">
                      "{selectedCommand.expectedResponse}"
                    </p>
                  </div>
                )}

                {/* RELATED COMMANDS */}
                {relatedCommands.length > 0 && (
                  <div className="pt-3 border-t border-[var(--glass-border)] space-y-2">
                    <div className="text-[11px] font-mono uppercase text-[var(--text-faint)]">
                      RELATED IN {selectedCommand.category}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {relatedCommands.map((rel) => (
                        <button
                          key={rel.id}
                          type="button"
                          onClick={() => setSelectedCommandId(rel.id)}
                          className="px-2.5 py-1 rounded-lg glass-soft hover:border-[var(--glass-border-strong)] text-xs font-mono text-[var(--ice-silver)] hover:underline flex items-center gap-1 cursor-pointer"
                        >
                          <span>{rel.name}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="glass-strong rounded-2xl p-8 text-center text-xs text-[var(--text-muted)]">
                Select a command from the list to view full parameter rules and syntax.
              </div>
            )}
          </div>
        </div>

        {/* MOBILE/TABLET DETAIL BOTTOM SHEET */}
        {mobileDetailOpen && selectedCommand && (
          <div className="fixed inset-0 z-50 lg:hidden flex flex-col justify-end">
            <div
              className="fixed inset-0 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150"
              onClick={() => setMobileDetailOpen(false)}
            />

            <div className="relative glass-strong rounded-t-3xl max-h-[85vh] overflow-y-auto p-6 z-10 border-t border-[var(--glass-border-strong)] space-y-5 animate-in slide-in-from-bottom duration-200">
              <div className="flex items-center justify-between border-b border-[var(--glass-border)] pb-3">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm text-[var(--hint)] uppercase">
                    {selectedCommand.category}
                  </span>
                  <span>•</span>
                  <TierDot tier={selectedCommand.tier} />
                </div>
                <button
                  type="button"
                  onClick={() => setMobileDetailOpen(false)}
                  className="p-1 text-[var(--text-faint)] hover:text-[var(--ice-silver)] rounded"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div>
                <h3 className="font-mono font-bold text-2xl text-[var(--ice-silver)]">
                  {selectedCommand.name}
                </h3>
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  {selectedCommand.description}
                </p>
              </div>

              <div className="space-y-1">
                <div className="text-[11px] font-mono text-[var(--text-faint)]">SYNTAX</div>
                <div className="bg-black/40 p-3 rounded-xl font-mono text-xs text-[var(--ice-silver)] flex items-center justify-between">
                  <code>{selectedCommand.syntax}</code>
                  <button
                    type="button"
                    onClick={() => copyText(selectedCommand.syntax, selectedCommand.id)}
                    className="p-1 glass-soft rounded"
                  >
                    {copiedId === selectedCommand.id ? (
                      <Check className="w-4 h-4 text-[var(--success)]" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              <div className="space-y-1">
                <div className="text-[11px] font-mono text-[var(--text-faint)]">EXAMPLE</div>
                <div className="bg-black/40 p-3 rounded-xl font-mono text-xs text-[var(--ice-silver)] flex items-center justify-between">
                  <code>{selectedCommand.example}</code>
                  <button
                    type="button"
                    onClick={() => copyText(selectedCommand.example, `${selectedCommand.id}-mex`)}
                    className="p-1 glass-soft rounded"
                  >
                    {copiedId === `${selectedCommand.id}-mex` ? (
                      <Check className="w-4 h-4 text-[var(--success)]" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function CommandsDirectoryPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[var(--bg-deep)] text-[var(--ice-silver)] flex items-center justify-center font-mono text-xs">
          Loading command database...
        </div>
      }
    >
      <CommandsDirectoryContent />
    </Suspense>
  );
}
