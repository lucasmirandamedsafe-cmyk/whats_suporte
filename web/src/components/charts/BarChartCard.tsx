"use client";
import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { FONT_FAMILY, INK } from "./chartTheme";

interface Props<T extends object> {
  data: T[];
  xKey: keyof T & string;
  yKey: keyof T & string;
  color: string;
  showValueLabels?: boolean;
  xTickInterval?: number;
}

export function BarChartCard<T extends object>({
  data,
  xKey,
  yKey,
  color,
  showValueLabels,
  xTickInterval,
}: Props<T>) {
  return (
    <div style={{ width: "100%", height: 280, fontFamily: FONT_FAMILY }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 16, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={INK.grid} vertical={false} />
          <XAxis
            dataKey={xKey as string}
            tick={{ fill: INK.secondary, fontSize: 12 }}
            interval={xTickInterval}
            axisLine={{ stroke: INK.grid }}
            tickLine={false}
          />
          <YAxis tick={{ fill: INK.secondary, fontSize: 12 }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{ background: "#ffffff", border: `1px solid ${INK.grid}`, fontSize: 12 }}
            labelStyle={{ color: INK.primary }}
          />
          <Bar dataKey={yKey as string} fill={color} radius={[4, 4, 0, 0]}>
            {showValueLabels ? (
              <LabelList dataKey={yKey as string} position="top" fill={INK.secondary} fontSize={11} />
            ) : null}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
