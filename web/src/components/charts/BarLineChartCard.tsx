"use client";
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { FONT_FAMILY, INK } from "./chartTheme";

interface Props<T extends object> {
  data: T[];
  xKey: keyof T & string;
  barKey: keyof T & string;
  lineKey: keyof T & string;
  barColor: string;
  lineColor: string;
  barLabel: string;
  lineLabel: string;
}

export function BarLineChartCard<T extends object>({
  data,
  xKey,
  barKey,
  lineKey,
  barColor,
  lineColor,
  barLabel,
  lineLabel,
}: Props<T>) {
  return (
    <div style={{ width: "100%", height: 300, fontFamily: FONT_FAMILY }}>
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 16, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={INK.grid} vertical={false} />
          <XAxis
            dataKey={xKey as string}
            tick={{ fill: INK.secondary, fontSize: 12 }}
            axisLine={{ stroke: INK.grid }}
            tickLine={false}
          />
          <YAxis yAxisId="left" tick={{ fill: INK.secondary, fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis
            yAxisId="right"
            orientation="right"
            tick={{ fill: INK.secondary, fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{ background: "#ffffff", border: `1px solid ${INK.grid}`, fontSize: 12 }}
            labelStyle={{ color: INK.primary }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: INK.secondary }} />
          <Bar yAxisId="left" dataKey={barKey as string} name={barLabel} fill={barColor} radius={[4, 4, 0, 0]} />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey={lineKey as string}
            name={lineLabel}
            stroke={lineColor}
            strokeWidth={2}
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
