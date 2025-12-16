/**
 * API Route: /api/meal-requests
 * Handles meal request list retrieval and creation
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

/**
 * GET /api/meal-requests
 * Fetch meal requests with optional filtering
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

    // Call backend API
    const result = await serverApi.get("/requests/all", {
      params,
      useVersioning: true, // /api/v1/requests/all
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
    console.error("GET /api/meal-requests error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to fetch meal requests",
      },
      { status: 500 }
    );
  }
}

/**
 * POST /api/meal-requests
 * Create a new meal request
 */
export async function POST(request: NextRequest) {
  try {
    // Extract query parameters for requester_id and meal_type_id
    const { searchParams } = request.nextUrl;
    const requesterId = searchParams.get("requester_id");
    const mealTypeId = searchParams.get("meal_type_id");

    if (!requesterId || !mealTypeId) {
      return NextResponse.json(
        {
          ok: false,
          error: "invalid_params",
          message: "requester_id and meal_type_id are required",
        },
        { status: 400 }
      );
    }

    // Parse request body
    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { ok: false, error: "invalid_json", message: "Request body must be valid JSON" },
        { status: 400 }
      );
    }

    // Call backend API
    const result = await serverApi.post(
      "/requests/create-meal-request",
      body,
      {
        params: {
          requester_id: requesterId,
          meal_type_id: mealTypeId,
        },
        useVersioning: true, // /api/v1/requests/create-meal-request
      }
    );

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
      { status: 201 }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("POST /api/meal-requests error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to create meal request",
      },
      { status: 500 }
    );
  }
}
