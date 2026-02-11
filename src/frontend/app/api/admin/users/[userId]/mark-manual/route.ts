/**
 * API Route: /api/admin/users/[userId]/mark-manual
 * Marks a user as manual (non-HRIS)
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
 * Request body structure
 */
interface MarkManualRequest {
  reason: string;
}

/**
 * POST /api/admin/users/[userId]/mark-manual
 * Mark a user as manual (changes user_source to 'manual')
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
      !("reason" in body) ||
      typeof (body as { reason: unknown }).reason !== "string" ||
      (body as { reason: string }).reason.trim().length < 20
    ) {
      return NextResponse.json(
        {
          ok: false,
          error: "invalid_request",
          message: "Request body must contain reason (min 20 characters)",
        },
        { status: 400 }
      );
    }

    // Forward to backend
    const result = await serverApi.post<UserWithRolesResponse>(
      `/admin/users/${userId}/mark-manual`,
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
        message: "User marked as manual successfully",
      },
      { status: 200 }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("POST /api/admin/users/[userId]/mark-manual error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to mark user as manual",
      },
      { status: 500 }
    );
  }
}
