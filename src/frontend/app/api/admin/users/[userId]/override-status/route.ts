/**
 * API Route: /api/admin/users/[userId]/override-status
 * Enables or disables status override for a user
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
  userSource: string;
  statusOverride: boolean;
  overrideReason: string | null;
  overrideSetById: string | null;
  overrideSetAt: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}

/**
 * Response structure from backend
 */
interface StatusOverrideResponse {
  user: UserWithRolesResponse;
  message: string;
}

/**
 * Request body structure
 */
interface OverrideStatusRequest {
  statusOverride: boolean;
  overrideReason?: string | null;
}

/**
 * POST /api/admin/users/[userId]/override-status
 * Enable or disable status override for a user
 * When enabled, HRIS sync will not modify this user's is_active status
 * Requires Super Admin role
 */
export async function POST(
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

    // Validate request body
    if (
      !body ||
      typeof body !== "object" ||
      !("statusOverride" in body) ||
      typeof (body as { statusOverride: unknown }).statusOverride !== "boolean"
    ) {
      return NextResponse.json(
        {
          ok: false,
          error: "invalid_request",
          message: "Request body must contain statusOverride boolean",
        },
        { status: 400 }
      );
    }

    const typedBody = body as OverrideStatusRequest;

    // Optional: validate reason if provided
    if (
      typedBody.statusOverride &&
      typedBody.overrideReason &&
      typeof typedBody.overrideReason === "string" &&
      typedBody.overrideReason.trim().length > 0 &&
      typedBody.overrideReason.trim().length < 20
    ) {
      return NextResponse.json(
        {
          ok: false,
          error: "invalid_request",
          message: "Override reason must be at least 20 characters if provided",
        },
        { status: 400 }
      );
    }

    // Forward to backend
    const result = await serverApi.post<StatusOverrideResponse>(
      `/admin/users/${userId}/override-status`,
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
        message: "User status override updated successfully",
      },
      { status: 200 }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("POST /api/admin/users/[userId]/override-status error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to update status override",
      },
      { status: 500 }
    );
  }
}
