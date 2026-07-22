"use client";
import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { FONT_FAMILY, INK } from "./chartTheme";

interface Props<T extends object> {
  data: T[];
  xKey: keyof T & string;
  yKey: keyof T & string;
  color: string;
  showValueLabels?: boolean;
}

export function HorizontalBarChartCard<T extends object>({ data, xKey, yKey, color, showValueLabels }: Props<T>) {
  const height = Math.max(200, data.length * 36 + 40);
  return (
    <div style={{ width: "100%", height, fontFamily: FONT_FAMILY }}>
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ top: 10, right: 24, left: 10, bottom: 0 }}>
          <CartesianGrid stroke={INK.grid} horizontal={false} />
          <XAxis type="number" tick={{ fill: INK.secondary, fontSize: 12 }} axisLine={{ stroke: INK.grid }} tickLine={false} />
          <YAxis
            type="category"
            dataKey={yKey as string}
            width={150}
            tick={{ fill: INK.secondary, fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip contentStyle={{ background: "#ffffff", border: `1px solid ${INK.grid}`, fontSize: 12 }} />
          <Bar dataKey={xKey as string} fill={color} radius={[0, 4, 4, 0]}>
            {showValueLabels ? (
              <LabelList dataKey={xKey as string} position="right" fill={INK.secondary} fontSize={11} />
            ) : null}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
