/**
 * API Route: /api/auth/roles/[roleId]/pages
 * Handles fetching and updating pages assigned to a role
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

/**
 * Backend response structure for role pages
 */
interface RolePageInfo {
  id: number;
  nameEn: string;
  nameAr: string;
  descriptionEn: string | null;
  descriptionAr: string | null;
  path: string | null;
  icon: string | null;
  navType: string | null;
  order: number;
  isMenuGroup: boolean;
  showInNav: boolean;
  openInNewTab: boolean;
  parentId: number | null;
  key: string | null;
  name: string;
  description: string | null;
}

interface RolePagesResponse {
  roleId: string;
  pages: RolePageInfo[];
  total: number;
}

/**
 * GET /api/auth/roles/[roleId]/pages
 * Fetch pages assigned to a specific role
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
    const url = `/auth/roles/${roleIdNum}/pages${queryString ? `?${queryString}` : ""}`;

    // Call backend with versioning
    const result = await serverApi.get<RolePagesResponse>(url, {
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

    // Return the full response object (roleId, pages, total)
    return NextResponse.json(
      {
        ok: true,
        data: result.data,
      },
      { status: 200 }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("GET /api/auth/roles/[roleId]/pages error:", errorMessage);

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
 * PUT /api/auth/roles/[roleId]/pages
 * Update pages assigned to a role (replaces all existing assignments)
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

    // Validate request body has pageIds
    if (
      !body ||
      typeof body !== "object" ||
      !("pageIds" in body) ||
      !Array.isArray((body as { pageIds: unknown }).pageIds)
    ) {
      return NextResponse.json(
        {
          ok: false,
          error: "invalid_request",
          message: "Request body must contain pageIds array",
        },
        { status: 400 }
      );
    }

    // Forward to backend (body should be in camelCase with pageIds)
    const result = await serverApi.put<RolePagesResponse>(
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
        data: result.data,
        message: "Role pages updated successfully",
      },
      { status: 200 }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("PUT /api/auth/roles/[roleId]/pages error:", errorMessage);

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
