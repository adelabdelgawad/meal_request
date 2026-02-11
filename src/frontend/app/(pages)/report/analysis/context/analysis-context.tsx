'use client';

import { createContext, useContext, useState, ReactNode } from 'react';
import type { AnalyticsFilters, EmployeeAnalytics } from '@/types/analytics.types';

interface AnalysisContextType {
  filters: AnalyticsFilters;
  setFilters: (filters: AnalyticsFilters) => void;
  data: EmployeeAnalytics[];
  setData: (data: EmployeeAnalytics[]) => void;
}

const AnalysisContext = createContext<AnalysisContextType | null>(null);

export function AnalysisProvider({ children }: { children: ReactNode }) {
  const today = new Date();
  const startOfDay = new Date(today.setHours(0, 0, 0, 0)).toISOString();
  const endOfDay = new Date(today.setHours(23, 59, 59, 999)).toISOString();

  const [filters, setFilters] = useState<AnalyticsFilters>({
    startTime: startOfDay,
    endTime: endOfDay,
  });
  const [data, setData] = useState<EmployeeAnalytics[]>([]);

  return (
    <AnalysisContext.Provider value={{
      filters,
      setFilters,
      data,
      setData,
    }}>
      {children}
    </AnalysisContext.Provider>
  );
}

export function useAnalysis() {
  const context = useContext(AnalysisContext);
  if (!context) {
    throw new Error('useAnalysis must be used within AnalysisProvider');
  }
  return context;
}
