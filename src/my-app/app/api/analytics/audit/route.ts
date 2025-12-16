/**
 * API Route: /api/analytics/audit
 * Handles audit data retrieval
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

/**
 * GET /api/analytics/audit
 * Fetch audit data for a time range
 */
export async function GET(request: NextRequest) {
  try {
    // Extract query parameters
    const { searchParams } = request.nextUrl;
    const startTime = searchParams.get("start_time");
    const endTime = searchParams.get("end_time");
    const skip = searchParams.get("skip");
    const limit = searchParams.get("limit");
    const search = searchParams.get("search");

    // If no date range provided, return empty data
    if (!startTime || !endTime) {
      return NextResponse.json(
        {
          ok: true,
          data: {
            data: [],
            total: 0,
            skip: 0,
            limit: 0,
          },
        },
        { status: 200 }
      );
    }

    // Build params for backend API
    const params: Record<string, string> = {
      start_time: startTime,
      end_time: endTime,
    };

    // Add optional pagination parameters (don't default - let backend handle it)
    if (skip !== null) {
      params.skip = skip;
    }
    if (limit !== null) {
      params.limit = limit;
    }
    if (search) {
      params.search = search;
    }

    // Call backend API (no locale forwarding needed - backend returns bilingual fields)
    const result = await serverApi.get("/reports/audit", {
      params,
      useVersioning: true, // /api/v1/reports/audit
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

    // Backend now returns paginated response: { data: [...], total: number, skip: number, limit: number }
    // The entire paginated response needs to be nested inside the "data" field
    // so that mapResponse() extracts it correctly
    const paginatedResponse = result.data as {
      data: unknown[];
      total: number;
      skip: number;
      limit: number;
    };

    return NextResponse.json(
      {
        ok: true,
        data: {
          data: paginatedResponse.data,
          total: paginatedResponse.total,
          skip: paginatedResponse.skip,
          limit: paginatedResponse.limit,
        },
      },
      { status: 200 }
    );
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";
    console.error("GET /api/analytics/audit error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to fetch audit data",
      },
      { status: 500 }
    );
  }
}
