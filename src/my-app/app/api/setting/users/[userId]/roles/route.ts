/**
 * API Route: /api/setting/users/[userId]/roles
 * Handles user role assignments
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";
import type { UserResponse } from "@/types/users";

/**
 * PUT /api/setting/users/[userId]/roles
 * Update user role assignments
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

    // Forward to backend (body should already be in camelCase)
    const result = await serverApi.put<UserResponse>(
      `/auth/users/${userId}/roles`,
      body,
      { useVersioning: true }
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
    console.error("PUT /api/setting/users/[userId]/roles error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to update user roles",
      },
      { status: 500 }
    );
  }
}
