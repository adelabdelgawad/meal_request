"use server";

/**
 * Server Actions for Audit Reports
 * These functions run on the server and communicate with the backend API
 */

import { serverApi } from "@/lib/http/axios-server";
import type { AuditRecord, AuditFilters } from "@/types/analytics.types";

/**
 * Paginated response for audit report
 */
export interface PaginatedAuditResponse {
  data: AuditRecord[];
  total: number;
  skip: number;
  limit: number;
}

/**
 * Server action to fetch audit report data
 * Used for SSR data loading on the audit page
 * @param filters - Start and end time filters
 * @returns Paginated audit response with data and total count
 */
export async function getAuditReport(
  filters: AuditFilters
): Promise<PaginatedAuditResponse> {
  try {
    const params = {
      start_time: filters.startTime,
      end_time: filters.endTime,
    };

    // Call the backend endpoint
    const response = await serverApi.get("/reports/audit", {
      params,
      useVersioning: true, // This will call /api/v1/reports/audit
    });

    if (!response.ok) {
      console.error("Failed to fetch audit report:", response.error);
      return { data: [], total: 0, skip: 0, limit: 10 };
    }

    // Backend now returns paginated response: { data: [...], total: number, skip: number, limit: number }
    if (
      response.data &&
      typeof response.data === "object" &&
      "data" in response.data
    ) {
      const paginatedResponse = response.data as PaginatedAuditResponse;

      // Return the full paginated response
      if (Array.isArray(paginatedResponse.data)) {
        return paginatedResponse;
      }
    }

    // Handle direct array response (backward compatibility)
    if (Array.isArray(response.data)) {
      return {
        data: response.data as AuditRecord[],
        total: (response.data as AuditRecord[]).length,
        skip: 0,
        limit: 10,
      };
    }

    console.warn("Unexpected audit report response format:", response.data);
    return { data: [], total: 0, skip: 0, limit: 10 };
  } catch (error: unknown) {
    console.error("Failed to fetch audit report:", error);
    return { data: [], total: 0, skip: 0, limit: 10 };
  }
}
