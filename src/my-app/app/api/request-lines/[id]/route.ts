/**
 * API Route: /api/request-lines/[id]
 * Handles request line updates
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

interface RouteParams {
  params: Promise<{ id: string }>;
}

/**
 * PUT /api/request-lines/[id]
 * Update a request line
 */
export async function PUT(request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params;

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
    const result = await serverApi.put(`/requests/lines/${id}`, body, {
      useVersioning: true, // /api/v1/requests/lines/{id}
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
    console.error("PUT /api/request-lines/[id] error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to update request line",
      },
      { status: 500 }
    );
  }
}
