/**
 * API Route: /api/setting/meal-type-setup
 * Handles meal type list retrieval and creation
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";
import type { MealTypesResponse } from "@/types/meal-types";

/**
 * GET /api/setting/meal-type-setup
 * Fetch meal types list with pagination and filtering
 */
export async function GET(request: NextRequest) {
  try {
    // Extract query parameters
    const { searchParams } = request.nextUrl;
    const params: Record<string, string> = {};

    // Convert URL params to backend format
    const limit = searchParams.get("limit");
    const skip = searchParams.get("skip");
    const activeOnly = searchParams.get("active_only");

    if (limit) params.limit = limit;
    if (skip) params.skip = skip;
    if (activeOnly !== null) params.active_only = activeOnly;

    // Call backend API - /api/v1/meal-types/paginated
    const result = await serverApi.get<MealTypesResponse>("/meal-types/paginated", {
      params,
      useVersioning: true,
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

    return NextResponse.json(result.data);
  } catch (error) {
    console.error("Error fetching meal types:", error);
    return NextResponse.json(
      {
        ok: false,
        error: "Internal server error",
        message: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

/**
 * POST /api/setting/meal-type-setup
 * Create a new meal type
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Call backend API
    const result = await serverApi.post("/meal-types", body, {
      useVersioning: true,
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

    return NextResponse.json(result.data, { status: 201 });
  } catch (error) {
    console.error("Error creating meal type:", error);
    return NextResponse.json(
      {
        ok: false,
        error: "Internal server error",
        message: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
