"use server";

/**
 * Server Actions for Pages Management
 * These functions run on the server and communicate with the backend API
 */

import { serverApi } from "@/lib/http/axios-server";
import type { SettingPagesResponse, PageResponse } from "@/types/pages";

/**
 * Fetch all pages (for role-page assignment)
 */
export async function getPages(): Promise<SettingPagesResponse | null> {
  try {
    const result = await serverApi.get<SettingPagesResponse>("/admin/pages", {
      params: {
        limit: 1000, // Large limit to get all pages
        skip: 0,
      },
      useVersioning: true, // Requests /api/v1/admin/pages
    });

    if (result.ok && result.data) {
      return result.data;
    }

    if (!result.ok) {
      console.error("Failed to fetch pages:", result.error);
    }
    return null;
  } catch (error) {
    console.error("Error in getPages:", error);
    return null;
  }
}

/**
 * Fetch a single page by ID
 */
export async function getPageById(pageId: number): Promise<PageResponse | null> {
  try {
    const result = await serverApi.get<PageResponse>(`/admin/pages/${pageId}`, {
      useVersioning: true,
    });

    if (result.ok && result.data) {
      return result.data;
    }

    if (!result.ok) {
      console.error("Failed to fetch page:", result.error);
    }
    return null;
  } catch (error) {
    console.error("Error in getPageById:", error);
    return null;
  }
}
