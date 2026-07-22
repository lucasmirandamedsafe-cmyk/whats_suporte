export function KpiCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex-1 min-w-[150px] rounded-lg border border-[#e1e0d9] bg-white px-4 py-3">
      <div className="text-xs text-[#898781] mb-1">{label}</div>
      <div className="text-2xl font-semibold text-[#0b0b0b]">{value}</div>
    </div>
  );
}
