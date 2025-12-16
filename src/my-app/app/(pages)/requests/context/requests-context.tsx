'use client';

import { createContext, useContext, useState, ReactNode } from 'react';
import type { RequestsFilters } from '@/types/requests.types';

interface RequestsContextType {
  filters: RequestsFilters;
  setFilters: (filters: RequestsFilters) => void;
  selectedRequestId: number | null;
  setSelectedRequestId: (id: number | null) => void;
}

const RequestsContext = createContext<RequestsContextType | null>(null);

export function RequestsProvider({ children }: { children: ReactNode }) {
  const [filters, setFilters] = useState<RequestsFilters>({
    status: 'Any',
    page: 1,
    limit: 20,
  });
  const [selectedRequestId, setSelectedRequestId] = useState<number | null>(null);

  return (
    <RequestsContext.Provider value={{
      filters,
      setFilters,
      selectedRequestId,
      setSelectedRequestId,
    }}>
      {children}
    </RequestsContext.Provider>
  );
}

export function useRequests() {
  const context = useContext(RequestsContext);
  if (!context) {
    throw new Error('useRequests must be used within RequestsProvider');
  }
  return context;
}
