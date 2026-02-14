'use client';

import { ResponsiveContainer, AreaChart, Area } from 'recharts';

interface SparklineProps {
  data: number[];
  color?: string;
  height?: number;
}

/**
 * Minimal sparkline chart — no axes, no grid, no tooltip.
 * Ideal for inline metric cards showing 7/30-day trends.
 */
export function Sparkline({
  data,
  color = 'hsl(var(--primary))',
  height = 40,
}: SparklineProps) {
  if (data.length < 2) return null;

  const chartData = data.map((v, i) => ({ i, v }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
        <defs>
          <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="v"
          stroke={color}
          strokeWidth={1.5}
          fill="url(#sparkGrad)"
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
