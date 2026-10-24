"use client";

import React, { useEffect, useRef, useState } from "react";

export function CustomCursor() {
  const [hasMoved, setHasMoved] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [isTouch, setIsTouch] = useState(true);
  const [reducedMotion, setReducedMotion] = useState(false);

  const dotRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);

  // Position state refs to avoid unneeded re-renders
  const pos = useRef({ x: -100, y: -100 });
  const ringPos = useRef({ x: -100, y: -100 });
  const rafId = useRef<number | null>(null);

  useEffect(() => {
    // Check touch device or reduced motion
    const touchQuery = window.matchMedia("(pointer: coarse)");
    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

    setIsTouch(touchQuery.matches);
    setReducedMotion(motionQuery.matches);

    const handleTouchChange = (e: MediaQueryListEvent) => setIsTouch(e.matches);
    const handleMotionChange = (e: MediaQueryListEvent) => setReducedMotion(e.matches);

    touchQuery.addEventListener("change", handleTouchChange);
    motionQuery.addEventListener("change", handleMotionChange);

    if (touchQuery.matches) {
      return () => {
        touchQuery.removeEventListener("change", handleTouchChange);
        motionQuery.removeEventListener("change", handleMotionChange);
      };
    }

    const onMouseMove = (e: MouseEvent) => {
      // On the very first mouse move, sync coordinates immediately so ring doesn't lerp from top-left
      if (!hasMoved) {
        pos.current.x = e.clientX;
        pos.current.y = e.clientY;
        ringPos.current.x = e.clientX;
        ringPos.current.y = e.clientY;
        setHasMoved(true);
      } else {
        pos.current.x = e.clientX;
        pos.current.y = e.clientY;
      }

      // Check if hovering over interactive elements
      const target = e.target as HTMLElement | null;
      if (
        target &&
        (target.closest("button") ||
          target.closest("a") ||
          target.closest("input") ||
          target.closest("select") ||
          target.closest("textarea") ||
          target.closest('[role="button"]') ||
          target.classList.contains("interactive"))
      ) {
        setIsHovered(true);
      } else {
        setIsHovered(false);
      }
    };

    const onMouseLeave = () => setHasMoved(false);
    const onMouseEnter = (e: MouseEvent) => {
      pos.current.x = e.clientX;
      pos.current.y = e.clientY;
      ringPos.current.x = e.clientX;
      ringPos.current.y = e.clientY;
      setHasMoved(true);
    };

    window.addEventListener("mousemove", onMouseMove, { passive: true });
    document.addEventListener("mouseleave", onMouseLeave);
    document.addEventListener("mouseenter", onMouseEnter);

    // Render loop for smooth lerp on the outer ring
    const render = () => {
      if (reducedMotion) {
        ringPos.current.x = pos.current.x;
        ringPos.current.y = pos.current.y;
      } else {
        const ease = 0.18;
        ringPos.current.x += (pos.current.x - ringPos.current.x) * ease;
        ringPos.current.y += (pos.current.y - ringPos.current.y) * ease;
      }

      if (dotRef.current) {
        dotRef.current.style.transform = `translate3d(${pos.current.x}px, ${pos.current.y}px, 0)`;
      }

      if (ringRef.current) {
        ringRef.current.style.transform = `translate3d(${ringPos.current.x}px, ${ringPos.current.y}px, 0)`;
      }

      rafId.current = requestAnimationFrame(render);
    };

    rafId.current = requestAnimationFrame(render);

    return () => {
      touchQuery.removeEventListener("change", handleTouchChange);
      motionQuery.removeEventListener("change", handleMotionChange);
      window.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseleave", onMouseLeave);
      document.removeEventListener("mouseenter", onMouseEnter);
      if (rafId.current) cancelAnimationFrame(rafId.current);
    };
  }, [hasMoved, reducedMotion]);

  if (isTouch || !hasMoved) return null;

  return (
    <>
      {/* Inner precise dot */}
      <div
        ref={dotRef}
        aria-hidden="true"
        className={`pointer-events-none fixed top-0 left-0 z-[9999] -ml-1 -mt-1 w-2 h-2 rounded-full bg-[var(--text)] transition-transform duration-75 ${
          isHovered ? "scale-75 bg-[var(--accent)]" : "scale-100"
        }`}
        style={{ willChange: "transform" }}
      />

      {/* Outer lagging lerp ring */}
      <div
        ref={ringRef}
        aria-hidden="true"
        className={`pointer-events-none fixed top-0 left-0 z-[9998] rounded-full border transition-all duration-150 ease-out ${
          isHovered
            ? "-ml-6 -mt-6 w-12 h-12 border-[var(--accent)] bg-[var(--tint)] scale-100"
            : "-ml-4 -mt-4 w-8 h-8 border-[var(--border-strong)] bg-transparent scale-100"
        }`}
        style={{ willChange: "transform" }}
      />
    </>
  );
}
