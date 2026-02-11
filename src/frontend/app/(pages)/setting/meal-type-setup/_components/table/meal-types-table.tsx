"use client";

import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import { Pagination } from "@/components/data-table";
import { StatusPanel } from "../sidebar/status-panel";
import { MealTypesTableBody } from "./meal-types-table-body";
import { MealTypesDataProvider } from "@/app/(pages)/meal-type-setup/context/meal-types-data-context";
import { MealTypeModal } from "../modal/meal-type-modal";
import LoadingSkeleton from "@/components/loading-skeleton";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { clientApi } from "@/lib/http/axios-client";
import type { MealTypesResponse, MealTypeResponse } from "@/types/meal-types";

interface MealTypesTableProps {
  initialData: MealTypesResponse;
}

/**
 * Fetcher function for SWR
 */
const fetcher = async (url: string): Promise<MealTypesResponse> => {
  const response = await clientApi.get<MealTypesResponse>(url);
  if (!response.ok) {
    throw new Error(response.error || "Failed to fetch");
  }
  return response.data;
};

function MealTypesTable({ initialData }: MealTypesTableProps) {
  const searchParams = useSearchParams();

  // Read URL parameters
  const page = Number(searchParams?.get("page") || "1");
  const limit = Number(searchParams?.get("limit") || "10");
  const activeOnly = searchParams?.get("active_only") || "";

  // Build API URL with current filters
  const params = new URLSearchParams();
  params.append("skip", ((page - 1) * limit).toString());
  params.append("limit", limit.toString());
  if (activeOnly) {
    params.append("active_only", activeOnly);
  }

  const apiUrl = `/setting/meal-types?${params.toString()}`;

  // SWR hook
  const { data, mutate, isLoading, error } = useSWR<MealTypesResponse>(
    apiUrl,
    fetcher,
    {
      fallbackData: initialData ?? undefined,
      keepPreviousData: true,
      revalidateOnMount: false,
      revalidateIfStale: true,
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
    }
  );

  const mealTypes = data?.items ?? [];
  const activeCount = data?.activeCount ?? 0;
  const inactiveCount = data?.inactiveCount ?? 0;
  const totalItems = data?.total ?? 0;

  /**
   * Optimistic update helper
   */
  const updateMealTypes = async (updatedMealTypes: MealTypeResponse[]) => {
    const currentData = data || initialData;

    await mutate(
      async () => {
        const updatedItems = (currentData.items || []).map((mealType) => {
          const updated = updatedMealTypes.find((u) => u.id === mealType.id);
          return updated ? { ...mealType, ...updated } : mealType;
        });

        // Recalculate counts
        const newActiveCount = updatedItems.filter(
          (mt) => mt.isActive && !mt.isDeleted
        ).length;
        const newInactiveCount = updatedItems.filter(
          (mt) => !mt.isActive && !mt.isDeleted
        ).length;

        return {
          ...currentData,
          items: updatedItems,
          activeCount: newActiveCount,
          inactiveCount: newInactiveCount,
        };
      },
      { revalidate: false }
    );
  };

  /**
   * Add new meal type to cache
   */
  const addMealType = async (newMealType: MealTypeResponse) => {
    const currentData = data || initialData;

    await mutate(
      async () => {
        const updatedItems = [...(currentData.items || []), newMealType];

        // Recalculate counts
        const newActiveCount = updatedItems.filter(
          (mt) => mt.isActive && !mt.isDeleted
        ).length;
        const newInactiveCount = updatedItems.filter(
          (mt) => !mt.isActive && !mt.isDeleted
        ).length;

        return {
          ...currentData,
          items: updatedItems,
          total: (currentData.total || 0) + 1,
          activeCount: newActiveCount,
          inactiveCount: newInactiveCount,
        };
      },
      { revalidate: true }
    );
  };

  /**
   * Remove meal type from cache (soft delete)
   */
  const removeMealType = async (mealTypeId: number) => {
    const currentData = data || initialData;

    await mutate(
      async () => {
        const updatedItems = (currentData.items || []).map((mt) =>
          mt.id === mealTypeId ? { ...mt, isDeleted: true, isActive: false } : mt
        );

        // Recalculate counts
        const newActiveCount = updatedItems.filter(
          (mt) => mt.isActive && !mt.isDeleted
        ).length;
        const newInactiveCount = updatedItems.filter(
          (mt) => !mt.isActive && !mt.isDeleted
        ).length;

        return {
          ...currentData,
          items: updatedItems,
          activeCount: newActiveCount,
          inactiveCount: newInactiveCount,
        };
      },
      { revalidate: true }
    );
  };

  return (
    <ErrorBoundary>
      <MealTypesDataProvider>
        <div className="flex h-screen overflow-hidden bg-background">
          {/* Sidebar */}
          <div className="w-64 border-e border-border bg-card shrink-0">
            <StatusPanel
              activeCount={activeCount}
              inactiveCount={inactiveCount}
              totalCount={totalItems}
            />
          </div>

          {/* Main Content */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {isLoading && !data ? (
              <LoadingSkeleton />
            ) : error ? (
              <div className="flex items-center justify-center h-full">
                <p className="text-destructive">Error loading meal types</p>
              </div>
            ) : (
              <>
                <MealTypesTableBody
                  mealTypes={mealTypes}
                  updateMealTypes={updateMealTypes}
                  removeMealType={removeMealType}
                />

                {totalItems > 0 && (
                  <div className="border-t border-border p-4 bg-card">
                    <Pagination
                      currentPage={page}
                      totalItems={totalItems}
                      pageSize={limit}
                    />
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Modal */}
        <MealTypeModal
          addMealType={addMealType}
          updateMealTypes={updateMealTypes}
        />
      </MealTypesDataProvider>
    </ErrorBoundary>
  );
}

export default MealTypesTable;
