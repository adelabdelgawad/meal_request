/**
 * API Route: /api/setting/roles
 * Handles role list retrieval and creation
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";
import type { SettingRolesResponse, RoleResponse } from "@/types/roles";

/**
 * GET /api/setting/roles
 * Fetch roles list with pagination and filtering
 */
export async function GET(request: NextRequest) {
  try {
    // Extract query parameters
    const { searchParams } = request.nextUrl;
    const params: Record<string, string> = {};

    // Convert URL params to backend format (snake_case)
    const limit = searchParams.get("limit");
    const skip = searchParams.get("skip");
    const isActive = searchParams.get("is_active");
    const roleName = searchParams.get("role_name");
    const roleId = searchParams.get("role_id");

    if (limit) params.limit = limit;
    if (skip) params.skip = skip;
    if (isActive) params.is_active = isActive;
    if (roleName) params.role_name = roleName;
    if (roleId) params.role_id = roleId;

    // Call backend API - /api/v1/permissions/roles
    const result = await serverApi.get<SettingRolesResponse | Array<unknown>>("/permissions/roles", {
      params,
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

    // Backend returns array directly, so we need to transform it
    let responseData: SettingRolesResponse;

    if (Array.isArray(result.data)) {
      // Map array to SettingRolesResponse format
      // Normalize response: camelCase (CamelModel) takes priority, snake_case as fallback
      // eslint-disable-next-line @typescript-eslint/no-explicit-any -- Dynamic backend response normalization
      const roles = result.data.map((role: any) => ({
        id: role.id,
        nameEn: role.nameEn ?? role.name_en ?? role.name ?? '',
        nameAr: role.nameAr ?? role.name_ar ?? '',
        descriptionEn: role.descriptionEn ?? role.description_en ?? role.description ?? null,
        descriptionAr: role.descriptionAr ?? role.description_ar ?? null,
        name: role.name ?? role.nameEn ?? role.name_en ?? '',
        description: role.description ?? role.descriptionEn ?? role.description_en ?? null,
        isActive: role.isActive ?? role.is_active ?? true,
        createdAt: role.createdAt ?? role.created_at,
        updatedAt: role.updatedAt ?? role.updated_at,
        pagesNameEn: role.pagesNameEn ?? role.pages_name_en ?? null,
        pagesNameAr: role.pagesNameAr ?? role.pages_name_ar ?? null,
        totalUsers: role.totalUsers ?? role.total_users ?? 0,
      }));

      // Calculate counts from the array
      const activeCount = roles.filter((r: { isActive: boolean }) => r.isActive).length;
      const inactiveCount = roles.filter((r: { isActive: boolean }) => !r.isActive).length;

      responseData = {
        roles,
        total: roles.length,
        activeCount,
        inactiveCount,
      };
    } else {
      // Already in correct format
      responseData = result.data as SettingRolesResponse;
    }

    return NextResponse.json(
      {
        ok: true,
        data: responseData,
      },
      { status: 200 }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("GET /api/setting/roles error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to fetch roles",
      },
      { status: 500 }
    );
  }
}

/**
 * POST /api/setting/roles
 * Create a new role
 */
export async function POST(request: NextRequest) {
  try {
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
    const result = await serverApi.post<RoleResponse>("/auth/roles", body, {
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
      { status: 201 }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("POST /api/setting/roles error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to create role",
      },
      { status: 500 }
    );
  }
}
