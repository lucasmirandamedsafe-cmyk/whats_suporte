"use client";

interface Props {
  label: string;
  value: string | undefined;
  onChange: (value: string | undefined) => void;
  options: string[];
  sentinel: string;
}

export function SingleSelect({ label, value, onChange, options, sentinel }: Props) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-[#52514e]">{label}</span>
      <select
        className="rounded border border-[#e1e0d9] bg-white px-2 py-1.5 text-sm text-[#0b0b0b]"
        value={value ?? sentinel}
        onChange={(e) => {
          const v = e.target.value;
          onChange(v === sentinel ? undefined : v);
        }}
      >
        <option value={sentinel}>{sentinel}</option>
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}
