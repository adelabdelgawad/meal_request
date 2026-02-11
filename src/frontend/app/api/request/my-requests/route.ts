/**
 * API Route: /api/request/my-requests
 * Handles retrieval of current user's own meal requests
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

/**
 * GET /api/request/my-requests
 * Fetch meal requests created by current user
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

/**
 * GET /api/my-requests
 * Fetch meal requests created by the current user
 */
export async function GET(request: NextRequest) {
  try {
    // Extract query parameters
    const { searchParams } = request.nextUrl;
    const params: Record<string, string> = {};

    // Convert URL params to backend format
    searchParams.forEach((value, key) => {
      params[key] = value;
    });

    // Call backend API - /requests/my endpoint filters by current user
    const result = await serverApi.get("/requests/my", {
      params,
      useVersioning: true, // /api/v1/requests/my
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
    console.error("GET /api/request/my-requests error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to fetch your meal requests",
      },
      { status: 500 }
    );
  }
}
