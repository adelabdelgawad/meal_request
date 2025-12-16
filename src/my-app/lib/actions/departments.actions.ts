"use server";

/**
 * Server Actions for Departments
 * These functions run on the server and communicate with the backend API
 */

import { serverApi } from "@/lib/http/axios-server";

export interface DepartmentForAssignment {
  id: number;
  nameEn: string;
  nameAr: string;
}

interface DepartmentBackendResponse {
  id: number;
  nameEn?: string;
  name_en?: string;
  nameAr?: string;
  name_ar?: string;
}

/**
 * Fetch all departments for assignment UI
 * Returns a simplified list suitable for the department assignment sheet
 */
export async function getAllDepartments(): Promise<DepartmentForAssignment[]> {
  try {
    const result = await serverApi.get<DepartmentBackendResponse[]>("/departments", {
      params: {
        page: 1,
        per_page: 1000, // Get all departments
      },
      useVersioning: true,
    });

    if (result.ok && result.data) {
      // Normalize response: camelCase takes priority, snake_case as fallback
      return result.data.map((dept) => ({
        id: dept.id,
        nameEn: dept.nameEn ?? dept.name_en ?? "",
        nameAr: dept.nameAr ?? dept.name_ar ?? "",
      }));
    }

    return [];
  } catch (error) {
    console.error("Failed to fetch departments:", error);
    return [];
  }
}
