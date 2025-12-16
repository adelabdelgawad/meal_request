/**
 * API Route: /api/auth/users/status
 * Handles bulk user status updates
 * Proxies to backend: PUT /api/v1/auth/users/status
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

interface BulkStatusUpdateRequest {
  userIds: string[];
  isActive: boolean;
}

interface BulkStatusUpdateResponse {
  updatedUsers: unknown[];
  updatedCount: number;
}

/**
 * PUT /api/auth/users/status
 * Bulk update user status
 */
export async function PUT(request: NextRequest) {
  try {
    let body: BulkStatusUpdateRequest;
    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { ok: false, error: "invalid_json", message: "Request body must be valid JSON" },
        { status: 400 }
      );
    }

    // Validate required fields
    if (!body.userIds || !Array.isArray(body.userIds) || body.userIds.length === 0) {
      return NextResponse.json(
        { ok: false, error: "validation_error", message: "userIds must be a non-empty array" },
        { status: 400 }
      );
    }

    if (typeof body.isActive !== "boolean") {
      return NextResponse.json(
        { ok: false, error: "validation_error", message: "isActive must be a boolean" },
        { status: 400 }
      );
    }

    // Call backend with versioning enabled
    const result = await serverApi.put<BulkStatusUpdateResponse>(
      "/auth/users/status",
      body,
      {
        useVersioning: true,
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
    console.error("PUT /api/auth/users/status error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to bulk update user status",
      },
      { status: 500 }
    );
  }
}
