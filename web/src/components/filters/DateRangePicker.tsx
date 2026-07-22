"use client";

interface Props {
  start: string | undefined;
  end: string | undefined;
  minDate?: string | null;
  maxDate?: string | null;
  onChange: (start: string | undefined, end: string | undefined) => void;
}

export function DateRangePicker({ start, end, minDate, maxDate, onChange }: Props) {
  return (
    <div className="flex flex-col gap-1 text-sm">
      <span className="text-[#52514e]">Período</span>
      <div className="flex items-center gap-2">
        <input
          type="date"
          className="rounded border border-[#e1e0d9] bg-white px-2 py-1.5 text-sm text-[#0b0b0b]"
          value={start ?? minDate ?? ""}
          min={minDate ?? undefined}
          max={maxDate ?? undefined}
          onChange={(e) => onChange(e.target.value || undefined, end)}
        />
        <span className="text-[#898781]">até</span>
        <input
          type="date"
          className="rounded border border-[#e1e0d9] bg-white px-2 py-1.5 text-sm text-[#0b0b0b]"
          value={end ?? maxDate ?? ""}
          min={minDate ?? undefined}
          max={maxDate ?? undefined}
          onChange={(e) => onChange(start, e.target.value || undefined)}
        />
      </div>
    </div>
  );
}
