import { serverApi } from '@/lib/http/axios-server';
import type { EmployeeAnalytics, AuditRecord } from '@/types/analytics.types';

export async function getRequestAnalysis(startTime: string, endTime: string): Promise<EmployeeAnalytics[]> {
  try {
    const response = await serverApi.get<EmployeeAnalytics[]>(
      `/request-analysis?start_time=${encodeURIComponent(startTime)}&end_time=${encodeURIComponent(endTime)}`,
      { useVersioning: true }
    );
    if (!response.ok) {
      console.error('Failed to fetch analytics:', 'error' in response ? response.error : 'Unknown error');
      return [];
    }
    return response.data || [];
  } catch (error) {
    console.error('Failed to fetch analytics:', error);
    return [];
  }
}

export async function getAuditData(startTime: string, endTime: string): Promise<AuditRecord[]> {
  try {
    const response = await serverApi.get<AuditRecord[]>(
      `/audit-request?start_time=${encodeURIComponent(startTime)}&end_time=${encodeURIComponent(endTime)}`,
      { useVersioning: true }
    );
    if (!response.ok) {
      console.error('Failed to fetch audit data:', 'error' in response ? response.error : 'Unknown error');
      return [];
    }
    return response.data || [];
  } catch (error) {
    console.error('Failed to fetch audit data:', error);
    return [];
  }
}
