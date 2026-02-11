/**
 * API Route: /api/request-lines
 * Handles request line retrieval
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

/**
 * GET /api/request-lines
 * Fetch request lines for a specific meal request
 */
export async function GET(request: NextRequest) {
  try {
    // Extract query parameters
    const { searchParams } = request.nextUrl;
    const requestId = searchParams.get("request_id");

    if (!requestId) {
      return NextResponse.json(
        {
          ok: false,
          error: "invalid_params",
          message: "request_id is required",
        },
        { status: 400 }
      );
    }

    // Call backend API
    const result = await serverApi.get("/requests/lines", {
      params: {
        request_id: requestId,
      },
      useVersioning: true, // /api/v1/requests/lines
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
    console.error("GET /api/request-lines error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to fetch request lines",
      },
      { status: 500 }
    );
  }
}
