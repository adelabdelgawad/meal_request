/**
 * API Route: /api/request/requests/stats
 * Handles meal request statistics (counts by status)
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

/**
 * GET /api/request/requests/stats
 * Fetch meal request statistics with optional filtering
 */
export async function GET(request: NextRequest) {
  try {
    // Extract query parameters for filtering
    const { searchParams } = request.nextUrl;
    const params: Record<string, string> = {};

    // Convert URL params to backend format
    searchParams.forEach((value, key) => {
      params[key] = value;
    });

    // Call backend API with filters
    const result = await serverApi.get("/requests/stats", {
      params,
      useVersioning: true, // /api/v1/requests/stats
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
    console.error("GET /api/request/requests/stats error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to fetch meal request statistics",
      },
      { status: 500 }
    );
  }
}
