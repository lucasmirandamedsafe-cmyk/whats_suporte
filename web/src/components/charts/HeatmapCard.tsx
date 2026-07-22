"use client";
import { FONT_FAMILY, INK } from "./chartTheme";

interface Props<T extends object> {
  data: T[];
  rowKey: keyof T & string;
  colKey: keyof T & string;
  valueKey: keyof T & string;
  rows: string[];
  cols: string[];
  color: string;
}

function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace("#", "");
  const num = parseInt(clean, 16);
  return [(num >> 16) & 255, (num >> 8) & 255, num & 255];
}

function formatPct(value: number, total: number): string {
  if (total <= 0) return "0%";
  return `${((value / total) * 100).toFixed(1)}%`;
}

function Cell({
  value,
  total,
  intensity,
  color,
  bold,
}: {
  value: number;
  total: number;
  intensity: number | null;
  color: [number, number, number];
  bold?: boolean;
}) {
  const [r, g, b] = color;
  const background =
    intensity === null ? INK.grid : `rgba(${r}, ${g}, ${b}, ${0.06 + intensity * 0.94})`;
  const textColor = intensity !== null && intensity > 0.6 ? "#ffffff" : INK.primary;

  return (
    <td
      className={`p-2 text-center rounded ${bold ? "font-semibold" : ""}`}
      style={{ background, color: textColor, minWidth: 40 }}
    >
      {formatPct(value, total)}
    </td>
  );
}

export function HeatmapCard<T extends object>({ data, rowKey, colKey, valueKey, rows, cols, color }: Props<T>) {
  const lookup = new Map<string, number>();
  let max = 0;
  let grandTotal = 0;
  for (const row of data) {
    const key = `${row[rowKey]}|${row[colKey]}`;
    const value = Number(row[valueKey] ?? 0);
    lookup.set(key, value);
    if (value > max) max = value;
    grandTotal += value;
  }

  const rowTotals = new Map<string, number>();
  const colTotals = new Map<string, number>();
  for (const row of rows) {
    let total = 0;
    for (const col of cols) total += lookup.get(`${row}|${col}`) ?? 0;
    rowTotals.set(row, total);
  }
  for (const col of cols) {
    let total = 0;
    for (const row of rows) total += lookup.get(`${row}|${col}`) ?? 0;
    colTotals.set(col, total);
  }

  const rgb = hexToRgb(color);

  return (
    <div style={{ fontFamily: FONT_FAMILY }} className="overflow-x-auto">
      <table className="border-collapse text-xs w-full">
        <thead>
          <tr>
            <th className="p-2 text-left font-medium" style={{ color: INK.secondary }} />
            {cols.map((col) => (
              <th
                key={col}
                className="p-2 text-center font-medium whitespace-nowrap"
                style={{ color: INK.secondary }}
              >
                {col}
              </th>
            ))}
            <th className="p-2 text-center font-semibold whitespace-nowrap" style={{ color: INK.secondary }}>
              Total
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row}>
              <td className="p-2 font-medium whitespace-nowrap" style={{ color: INK.secondary }}>
                {row}
              </td>
              {cols.map((col) => {
                const value = lookup.get(`${row}|${col}`) ?? 0;
                const intensity = max > 0 ? value / max : 0;
                return <Cell key={col} value={value} total={grandTotal} intensity={intensity} color={rgb} />;
              })}
              <Cell value={rowTotals.get(row) ?? 0} total={grandTotal} intensity={null} color={rgb} bold />
            </tr>
          ))}
          <tr>
            <td className="p-2 font-semibold whitespace-nowrap" style={{ color: INK.secondary }}>
              Total
            </td>
            {cols.map((col) => (
              <Cell key={col} value={colTotals.get(col) ?? 0} total={grandTotal} intensity={null} color={rgb} bold />
            ))}
            <Cell value={grandTotal} total={grandTotal} intensity={null} color={rgb} bold />
          </tr>
        </tbody>
      </table>
    </div>
  );
}
