/**
 * API Route: /api/setting/users
 * Handles user list retrieval and creation
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";
import type { SettingUsersResponse, UserCreate } from "@/types/users";

/**
 * GET /api/setting/users
 * Fetch users list with pagination and filtering
 */
export async function GET(request: NextRequest) {
  try {
    // Extract query parameters
    const { searchParams } = request.nextUrl;
    const params: Record<string, string> = {};

    // Convert URL params to backend format (snake_case)
    const limit = searchParams.get("limit");
    const skip = searchParams.get("skip");
    const username = searchParams.get("username");
    const isActive = searchParams.get("is_active");
    const role = searchParams.get("role");

    if (limit) params.limit = limit;
    if (skip) params.skip = skip;
    if (username) params.username = username;
    if (isActive) params.is_active = isActive;
    if (role) params.role = role;

    // Call backend API
    const result = await serverApi.get<SettingUsersResponse>("/auth/users", {
      params,
      useVersioning: true, // /api/v1/auth/users
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
    console.error("GET /api/setting/users error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to fetch users",
      },
      { status: 500 }
    );
  }
}

/**
 * POST /api/setting/users
 * Create a new user
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
    const result = await serverApi.post<UserCreate>("/auth/users", body, {
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
    console.error("POST /api/setting/users error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to create user",
      },
      { status: 500 }
    );
  }
}
