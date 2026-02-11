/**
 * API Route: /api/request/requests/[id]
 * Handles meal request updates
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

interface RouteParams {
  params: Promise<{ id: string }>;
}

/**
 * PUT /api/request/requests/[id]
 * Update a meal request status
 */
export async function PUT(request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params;

    // Extract query parameters for status_id and account_id
    const { searchParams } = request.nextUrl;
    const statusId = searchParams.get("status_id");
    const accountId = searchParams.get("account_id");

    if (!statusId || !accountId) {
      return NextResponse.json(
        {
          ok: false,
          error: "invalid_params",
          message: "status_id and account_id are required",
        },
        { status: 400 }
      );
    }

    // Call backend API
    const result = await serverApi.put(
      "/requests/update-meal-request",
      undefined,
      {
        params: {
          meal_request_id: id,
          status_id: statusId,
          account_id: accountId,
        },
        useVersioning: true, // /api/v1/requests/update-meal-request
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
      { status: 200 }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("PUT /api/request/requests/[id] error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to update meal request",
      },
      { status: 500 }
    );
  }
}
