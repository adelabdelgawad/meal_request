/**
 * API Route: /api/auth/users/[userId]/block
 * Handles blocking/unblocking a user
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

/**
 * Backend response structure for user with roles
 */
interface UserWithRolesResponse {
  id: string;
  username: string;
  email: string | null;
  fullName: string | null;
  title: string | null;
  isActive: boolean;
  isDomainUser: boolean;
  isSuperAdmin: boolean;
  isBlocked: boolean;
  roleId: number | null;
  roles: string[];
  roleIds: number[];
  assignedDepartmentCount: number;
  createdAt: string | null;
  updatedAt: string | null;
}

/**
 * PATCH /api/auth/users/[userId]/block
 * Toggle user blocked status
 */
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ userId: string }> }
) {
  try {
    const { userId } = await params;

    // Validate UUID format
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(userId)) {
      return NextResponse.json(
        { ok: false, error: "invalid_user_id", message: "User ID must be a valid UUID" },
        { status: 400 }
      );
    }

    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { ok: false, error: "invalid_json", message: "Request body must be valid JSON" },
        { status: 400 }
      );
    }

    // Validate request body has isBlocked
    if (
      !body ||
      typeof body !== "object" ||
      !("isBlocked" in body) ||
      typeof (body as { isBlocked: unknown }).isBlocked !== "boolean"
    ) {
      return NextResponse.json(
        {
          ok: false,
          error: "invalid_request",
          message: "Request body must contain isBlocked boolean",
        },
        { status: 400 }
      );
    }

    // Forward to backend (body should be in camelCase with isBlocked)
    const result = await serverApi.patch<UserWithRolesResponse>(
      `/auth/users/${userId}/block`,
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
        message: "User block status updated successfully",
      },
      { status: 200 }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("PATCH /api/auth/users/[userId]/block error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to update user block status",
      },
      { status: 500 }
    );
  }
}
