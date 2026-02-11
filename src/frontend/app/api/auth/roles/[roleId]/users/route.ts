/**
 * API Route: /api/auth/roles/[roleId]/users
 * Handles fetching and updating users assigned to a role
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

/**
 * Backend response structure for role users
 */
interface RoleUserInfo {
  id: string;
  username: string;
  fullName: string | null;
}

interface RoleUsersResponse {
  roleId: number;
  users: RoleUserInfo[];
  total: number;
}

/**
 * GET /api/auth/roles/[roleId]/users
 * Fetch users assigned to a specific role
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ roleId: string }> }
) {
  try {
    const { roleId } = await params;
    const roleIdNum = parseInt(roleId, 10);

    if (isNaN(roleIdNum)) {
      return NextResponse.json(
        { ok: false, error: "invalid_role_id", message: "Role ID must be a number" },
        { status: 400 }
      );
    }

    const { searchParams } = new URL(request.url);

    // Build query parameters - convert camelCase to snake_case for backend
    const queryParams = new URLSearchParams();
    const includeInactive = searchParams.get("includeInactive");
    if (includeInactive !== null) {
      queryParams.append("include_inactive", includeInactive);
    }

    const queryString = queryParams.toString();
    const url = `/auth/roles/${roleIdNum}/users${queryString ? `?${queryString}` : ""}`;

    // Call backend with versioning
    const result = await serverApi.get<RoleUsersResponse>(url, {
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

    // Return the full response object (roleId, users, total)
    return NextResponse.json(
      {
        ok: true,
        data: result.data,
      },
      { status: 200 }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("GET /api/auth/roles/[roleId]/users error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to fetch role users",
      },
      { status: 500 }
    );
  }
}

/**
 * PUT /api/auth/roles/[roleId]/users
 * Update users assigned to a role (replaces all existing assignments)
 */
export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ roleId: string }> }
) {
  try {
    const { roleId } = await params;
    const roleIdNum = parseInt(roleId, 10);

    if (isNaN(roleIdNum)) {
      return NextResponse.json(
        { ok: false, error: "invalid_role_id", message: "Role ID must be a number" },
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

    // Validate request body has userIds
    if (
      !body ||
      typeof body !== "object" ||
      !("userIds" in body) ||
      !Array.isArray((body as { userIds: unknown }).userIds)
    ) {
      return NextResponse.json(
        {
          ok: false,
          error: "invalid_request",
          message: "Request body must contain userIds array",
        },
        { status: 400 }
      );
    }

    // Forward to backend (body should be in camelCase with userIds)
    const result = await serverApi.put<RoleUsersResponse>(
      `/auth/roles/${roleIdNum}/users`,
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
        message: "Role users updated successfully",
      },
      { status: 200 }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("PUT /api/auth/roles/[roleId]/users error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to update role users",
      },
      { status: 500 }
    );
  }
}
