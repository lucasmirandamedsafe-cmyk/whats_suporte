interface Column<T> {
  key: keyof T;
  header: string;
  render?: (value: T[keyof T], row: T) => React.ReactNode;
}

interface Props<T> {
  columns: Column<T>[];
  rows: T[];
  emptyMessage?: string;
}

export function DataTable<T extends object>({ columns, rows, emptyMessage }: Props<T>) {
  if (rows.length === 0) {
    return <div className="text-sm text-[#898781] py-4">{emptyMessage ?? "Nenhum dado."}</div>;
  }

  return (
    <div className="overflow-auto max-h-[420px] border border-[#e1e0d9] rounded">
      <table className="w-full text-sm border-collapse">
        <thead className="sticky top-0 bg-[#f0efe9]">
          <tr>
            {columns.map((c) => (
              <th
                key={String(c.key)}
                className="text-left px-3 py-2 font-medium text-[#52514e] border-b border-[#e1e0d9] whitespace-nowrap"
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-[#e1e0d9] last:border-0 hover:bg-[#f7f6f2]">
              {columns.map((c) => (
                <td key={String(c.key)} className="px-3 py-2 text-[#0b0b0b] align-top">
                  {c.render ? c.render(row[c.key], row) : String(row[c.key] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
