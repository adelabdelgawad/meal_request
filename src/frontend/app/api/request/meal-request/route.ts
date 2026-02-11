/**
 * API Route: /api/request/meal-request/employees
 * Handles employee list retrieval for meal request page
 */

import { NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

/**
 * GET /api/request/meal-request/employees
 * Fetch employees list
 */
export async function GET() {
  try {
    // Call backend API
    const result = await serverApi.get("/employees", {
      useVersioning: true, // /api/v1/employees
    });

    if (!result.ok) {
      return NextResponse.json(
        {
          ok: false,
          error: result.error,
          message: result.message,
        },
        { status: result.status }
      );
    }

    return NextResponse.json(
      {
        ok: true,
        data: result.data,
      },
      { status: 200 }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("GET /api/request/meal-request/employees error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to fetch employees",
      },
      { status: 500 }
    );
  }
}
