/**
 * API Route: /api/setting/roles/[roleId]/pages
 * Handles role pages operations
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";
import type { PageResponse } from "@/types/pages";

/**
 * GET /api/setting/roles/[roleId]/pages
 * Fetch pages assigned to a role
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

    // Build query parameters
    const queryParams = new URLSearchParams();
    const includeInactive = searchParams.get("includeInactive");
    if (includeInactive !== null) {
      queryParams.append("include_inactive", includeInactive);
    }

    const queryString = queryParams.toString();
    const url = `/auth/roles/${roleIdNum}/pages${queryString ? `?${queryString}` : ""}`;

    const result = await serverApi.get<PageResponse[]>(url, {
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

    return NextResponse.json(
      {
        ok: true,
        data: result.data,
      },
      { status: 200 }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("GET /api/setting/roles/[roleId]/pages error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to fetch role pages",
      },
      { status: 500 }
    );
  }
}

/**
 * PUT /api/setting/roles/[roleId]/pages
 * Update pages assigned to a role
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

    // Forward to backend (body should already be in camelCase with pageIds)
    const result = await serverApi.put(
      `/auth/roles/${roleIdNum}/pages`,
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
        message: "Role pages updated successfully",
      },
      { status: 200 }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("PUT /api/setting/roles/[roleId]/pages error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to update role pages",
      },
      { status: 500 }
    );
  }
}
