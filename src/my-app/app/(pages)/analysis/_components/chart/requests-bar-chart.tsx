'use client';

import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { Bar, BarChart, XAxis, YAxis } from 'recharts';
import type { EmployeeAnalytics } from '@/types/analytics.types';

const chartConfig = {
  acceptedRequests: {
    label: 'Accepted Requests',
    color: 'hsl(var(--chart-1))',
  },
};

interface RequestsBarChartProps {
  data: EmployeeAnalytics[];
  loading?: boolean;
}

export function RequestsBarChart({ data, loading }: RequestsBarChartProps) {
  if (loading) {
    return (
      <div className="border rounded-lg p-4 min-h-[300px] flex items-center justify-center">
        <div className="animate-pulse text-muted-foreground">Loading chart...</div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="border rounded-lg p-4 min-h-[300px] flex items-center justify-center">
        <p className="text-muted-foreground">No data available for the selected date range</p>
      </div>
    );
  }

  return (
    <div className="border rounded-lg p-4">
      <ChartContainer config={chartConfig} className="min-h-[300px] w-full">
        <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 80 }}>
          <XAxis
            dataKey="name"
            angle={-45}
            textAnchor="end"
            height={100}
            tick={{ fontSize: 12 }}
            interval={0}
          />
          <YAxis />
          <ChartTooltip content={<ChartTooltipContent />} />
          <Bar
            dataKey="acceptedRequests"
            fill="var(--color-acceptedRequests)"
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ChartContainer>
    </div>
  );
}
