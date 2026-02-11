/**
 * API Route: /api/report/analysis
 * Handles request analysis and analytics
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

/**
 * GET /api/report/analysis
 * Fetch analytics data for a time range
 */
export async function GET(request: NextRequest) {
  try {
    // Extract query parameters
    const { searchParams } = request.nextUrl;
    const startTime = searchParams.get("start_time");
    const endTime = searchParams.get("end_time");

    if (!startTime || !endTime) {
      return NextResponse.json(
        {
          ok: false,
          error: "invalid_params",
          message: "start_time and end_time are required",
        },
        { status: 400 }
      );
    }

    // Call backend API
    const result = await serverApi.get("/analysis/request-analysis", {
      params: {
        start_time: startTime,
        end_time: endTime,
      },
      useVersioning: true, // /api/v1/analysis/request-analysis
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
    console.error("GET /api/report/analysis error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to fetch analytics",
      },
      { status: 500 }
    );
  }
}
