"use client";
import { useState } from "react";

import { INK } from "@/components/charts/chartTheme";

export function HelpTooltip({ text }: { text: string }) {
  const [open, setOpen] = useState(false);

  return (
    <span className="relative inline-flex items-center">
      <button
        type="button"
        aria-label="Ajuda"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={() => setOpen((o) => !o)}
        className="ml-1 inline-flex h-3.5 w-3.5 items-center justify-center rounded-full text-[9px] leading-none cursor-help"
        style={{ background: INK.grid, color: INK.secondary }}
      >
        ?
      </button>
      {open ? (
        <span
          role="tooltip"
          className="absolute left-1/2 top-full z-10 mt-1.5 w-56 -translate-x-1/2 rounded border p-2 text-left text-[11px] font-normal shadow-md"
          style={{ background: "#ffffff", borderColor: INK.grid, color: INK.secondary }}
        >
          {text}
        </span>
      ) : null}
    </span>
  );
}
