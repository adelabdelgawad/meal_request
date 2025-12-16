/**
 * Server-side API functions for Employees
 * Used in server components to fetch employee data
 */

import { serverApi } from "@/lib/http/axios-server";
import type { EmployeesByDepartment } from "@/types/meal-request.types";

/**
 * Fetch all employees grouped by department
 */
export async function getEmployees(): Promise<EmployeesByDepartment> {
  try {
    const response = await serverApi.get<EmployeesByDepartment>(
      "/employees/grouped",
      {
        useVersioning: true,
      }
    );


    if (!response.ok) {
      console.error("Failed to fetch employees:", response);
      return {};
    }

    return response.data || {};
  } catch (error) {
    console.error("Failed to fetch employees:", error);
    return {};
  }
}
