"use client";
import type { Granularidade } from "@/lib/types";

const OPTIONS: { value: Granularidade; label: string }[] = [
  { value: "dia", label: "Diária" },
  { value: "semana", label: "Semanal" },
  { value: "mes", label: "Mensal" },
];

export function GranularidadeToggle({
  value,
  onChange,
}: {
  value: Granularidade;
  onChange: (value: Granularidade) => void;
}) {
  return (
    <div className="flex gap-1 rounded border border-[#e1e0d9] p-0.5 bg-white">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={`px-2.5 py-1 text-xs rounded transition-colors ${
            value === opt.value ? "bg-[#2a78d6] text-white" : "text-[#52514e] hover:bg-[#f0efe9]"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
