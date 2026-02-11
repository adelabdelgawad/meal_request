/**
 * API Route: /api/request/requests/status-options
 * Handles fetching meal request status options
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

/**
 * GET /api/request/requests/status-options
 * Fetch available status options for meal requests
 */
export async function GET(request: NextRequest) {
  try {
    // Extract query parameters
    const { searchParams } = request.nextUrl;
    const activeOnly = searchParams.get('active_only') !== 'false'; // Default to true

    // Call backend API
    const result = await serverApi.get("/requests/status-options", {
      params: {
        active_only: activeOnly,
      },
      useVersioning: true, // /api/v1/requests/status-options
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
    console.error("GET /api/request/requests/status-options error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to fetch status options",
      },
      { status: 500 }
    );
  }
}
