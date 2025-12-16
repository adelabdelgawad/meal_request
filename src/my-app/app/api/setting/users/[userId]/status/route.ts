/**
 * API Route: /api/setting/users/[userId]/status
 * Handles user status toggle (active/inactive)
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";
import type { UserResponse } from "@/types/users";

/**
 * PUT /api/setting/users/[userId]/status
 * Toggle user active/inactive status
 */
export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ userId: string }> }
) {
  try {
    const { userId } = await params;

    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { ok: false, error: "invalid_json", message: "Request body must be valid JSON" },
        { status: 400 }
      );
    }

    // Forward to backend (body should contain userId and isActive in camelCase)
    const result = await serverApi.put<UserResponse>(
      `/auth/users/${userId}/status`,
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
    console.error("PUT /api/setting/users/[userId]/status error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to toggle user status",
      },
      { status: 500 }
    );
  }
}
