import { HelpTooltip } from "@/components/ui/HelpTooltip";

export function KpiCard({ label, value, help }: { label: string; value: string | number; help?: string }) {
  return (
    <div className="flex-1 min-w-[150px] rounded-lg border border-[#e1e0d9] bg-white px-4 py-3">
      <div className="flex items-center text-xs text-[#898781] mb-1">
        <span>{label}</span>
        {help ? <HelpTooltip text={help} /> : null}
      </div>
      <div className="text-2xl font-semibold text-[#0b0b0b]">{value}</div>
    </div>
  );
}
