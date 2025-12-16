import { AnalysisDataTable } from './_components/table/analysis-data-table';
import type { EmployeeAnalytics } from '@/types/analytics.types';
import { serverApi } from '@/lib/http/axios-server';

async function getInitialAnalyticsData(): Promise<EmployeeAnalytics[]> {
  try {
    // Default to today
    const today = new Date();
    const startTime = new Date(today.setHours(0, 0, 0, 0)).toISOString();
    const endTime = new Date(today.setHours(23, 59, 59, 999)).toISOString();

    const response = await serverApi.get<EmployeeAnalytics[]>(
      `/api/analytics?start_time=${encodeURIComponent(startTime)}&end_time=${encodeURIComponent(endTime)}`
    );

    if (response.ok && response.data) {
      return response.data;
    }

    return [];
  } catch (error) {
    console.error('Failed to fetch initial analytics data:', error);
    return [];
  }
}

export default async function AnalysisPage() {
  const initialData = await getInitialAnalyticsData();

  return (
    <div className="flex flex-col min-h-screen p-4 md:p-6 bg-background">
      <h1 className="text-2xl font-bold mb-4">Request Analysis</h1>
      <AnalysisDataTable initialData={initialData} />
    </div>
  );
}
