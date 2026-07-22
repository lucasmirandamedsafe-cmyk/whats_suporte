export function SectionHeader({ title, right }: { title: string; right?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-2">
      <h2 className="text-lg font-semibold text-[#0b0b0b]">{title}</h2>
      {right}
    </div>
  );
}
