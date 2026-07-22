"use client";

interface Props {
  label: string;
  options: string[];
  values: string[];
  onChange: (values: string[]) => void;
  labels?: Record<string, string>;
}

export function MultiSelect({ label, options, values, onChange, labels }: Props) {
  const toggle = (opt: string) => {
    if (values.includes(opt)) onChange(values.filter((v) => v !== opt));
    else onChange([...values, opt]);
  };

  return (
    <div className="flex flex-col gap-1 text-sm">
      <span className="text-[#52514e]">{label}</span>
      <div className="flex flex-col gap-1">
        {options.map((opt) => (
          <label key={opt} className="flex items-center gap-2 text-[#0b0b0b]">
            <input
              type="checkbox"
              checked={values.includes(opt)}
              onChange={() => toggle(opt)}
              className="accent-[#2a78d6]"
            />
            <span>{labels?.[opt] ?? opt}</span>
          </label>
        ))}
      </div>
    </div>
  );
}
