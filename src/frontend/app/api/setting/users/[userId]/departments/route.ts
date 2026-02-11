/**
 * API Route: /api/setting/users/[userId]/departments
 * Handles user department assignments (which departments' meal requests a user can view)
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

interface UserDepartmentsResponse {
  userId: string;
  departmentIds: number[];
}

/**
 * GET /api/setting/users/[userId]/departments
 * Get department IDs assigned to a user
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ userId: string }> }
) {
  try {
    const { userId } = await params;

    const result = await serverApi.get<UserDepartmentsResponse>(
      `/setting/users/${userId}/departments`,
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
    console.error("GET /api/setting/users/[userId]/departments error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to get user departments",
      },
      { status: 500 }
    );
  }
}

/**
 * PUT /api/setting/users/[userId]/departments
 * Update department assignments for a user
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

    const result = await serverApi.put<UserDepartmentsResponse>(
      `/setting/users/${userId}/departments`,
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
    console.error("PUT /api/setting/users/[userId]/departments error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to update user departments",
      },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/setting/users/[userId]/departments
 * Clear all department assignments for a user (user will see all departments)
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ userId: string }> }
) {
  try {
    const { userId } = await params;

    const result = await serverApi.delete(
      `/setting/users/${userId}/departments`,
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
      },
      { status: 200 }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("DELETE /api/setting/users/[userId]/departments error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to clear user departments",
      },
      { status: 500 }
    );
  }
}
