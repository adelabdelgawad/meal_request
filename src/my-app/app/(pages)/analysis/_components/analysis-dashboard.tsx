'use client';

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Download, BarChart3 } from 'lucide-react';
import { DateRangePicker } from './controls/date-range-picker';
import { RequestsBarChart } from './chart/requests-bar-chart';
import { SummaryTable } from './table/summary-table';
import type { EmployeeAnalytics } from '@/types/analytics.types';
import { useRouter } from 'next/navigation';
import { exportToExcel } from '@/lib/utils/export';
import { useLanguage, translate } from '@/hooks/use-language';

export function AnalysisDashboard() {
  const { t } = useLanguage();
  const router = useRouter();
  const [data, setData] = useState<EmployeeAnalytics[]>([]);
  const [loading, setLoading] = useState(true);

  // Default to today
  const today = new Date();
  const [startTime, setStartTime] = useState(
    new Date(today.setHours(0, 0, 0, 0)).toISOString()
  );
  const [endTime, setEndTime] = useState(
    new Date(today.setHours(23, 59, 59, 999)).toISOString()
  );

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `/api/analytics?start_time=${encodeURIComponent(startTime)}&end_time=${encodeURIComponent(endTime)}`
      );
      const result = await response.json();
      // Handle the API response format { ok: true, data: [...] }
      if (result.ok && result.data) {
        setData(result.data);
      } else {
        setData([]);
      }
    } catch (error) {
      console.error('Failed to load analytics:', error);
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [startTime, endTime]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleExportDetailed = () => {
    const params = new URLSearchParams({
      startTime,
      endTime,
    });
    router.push(`/audit?${params.toString()}`);
  };

  const handleExportResults = () => {
    // Export table to Excel using xlsx library
    if (data.length === 0) {
      alert(translate(t, 'analysis.alerts.noDataToExport'));
      return;
    }

    // Format data for export
    const exportData = data.map((item) => ({
      'English Name': item.name,
      'Total Approved Requests': item.acceptedRequests,
    }));

    exportToExcel(exportData, 'requestsData');
  };

  return (
    <div className="flex flex-col gap-6 flex-1">
      {/* Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex gap-2">
          <Button onClick={handleExportResults} className="bg-teal-500 hover:bg-teal-600">
            <Download className="mr-2 h-4 w-4" />
            Export Results
          </Button>
          <Button onClick={handleExportDetailed} className="bg-green-500 hover:bg-green-600">
            <BarChart3 className="mr-2 h-4 w-4" />
            Export Detailed
          </Button>
        </div>
        <DateRangePicker
          startTime={startTime}
          endTime={endTime}
          onStartTimeChange={setStartTime}
          onEndTimeChange={setEndTime}
        />
      </div>

      {/* Chart */}
      <RequestsBarChart data={data} loading={loading} />

      {/* Summary Table */}
      <SummaryTable data={data} loading={loading} />
    </div>
  );
}
