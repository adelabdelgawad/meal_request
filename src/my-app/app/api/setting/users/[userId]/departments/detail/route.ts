/**
 * API Route: /api/setting/users/[userId]/departments/detail
 * Get detailed department assignment info for a user
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

interface DepartmentForAssignment {
  id: number;
  nameEn: string;
  nameAr: string;
  isAssigned: boolean;
}

interface UserDepartmentsDetailResponse {
  userId: string;
  userName: string | null;
  assignedDepartmentIds: number[];
  departments: DepartmentForAssignment[];
}

/**
 * GET /api/setting/users/[userId]/departments/detail
 * Get all departments with assignment status for a user
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ userId: string }> }
) {
  try {
    const { userId } = await params;

    const result = await serverApi.get<UserDepartmentsDetailResponse>(
      `/setting/users/${userId}/departments/detail`,
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
    console.error("GET /api/setting/users/[userId]/departments/detail error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to get user departments detail",
      },
      { status: 500 }
    );
  }
}
