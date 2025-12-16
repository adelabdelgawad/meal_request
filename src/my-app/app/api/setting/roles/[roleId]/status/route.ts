/**
 * API Route: /api/setting/roles/[roleId]/status
 * Handles role status toggle operations
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";
import type { RoleResponse } from "@/types/roles";

/**
 * PUT /api/setting/roles/[roleId]/status
 * Toggle role active/inactive status
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

    // Forward to backend (body should already be in camelCase with roleId and isActive)
    const result = await serverApi.put<RoleResponse>(
      `/auth/roles/${roleIdNum}/status`,
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
    console.error("PUT /api/setting/roles/[roleId]/status error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to toggle role status",
      },
      { status: 500 }
    );
  }
}
