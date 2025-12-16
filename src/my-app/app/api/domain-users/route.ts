/**
 * API Route: /api/domain-users
 * Handles domain user list retrieval with search and pagination
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

interface DomainUserResponse {
  id: number;
  username: string;
  fullName: string | null;
  title: string | null;
  office: string | null;
  phone: string | null;
  manager: string | null;
  createdAt: string;
  updatedAt: string;
}

interface DomainUserListResponse {
  items: DomainUserResponse[];
  total: number;
  page: number;
  limit: number;
  hasMore: boolean;
}

/**
 * GET /api/domain-users
 * Fetch domain users with pagination and search
 *
 * Query params:
 * - q: Search query (matches username or fullName)
 * - page: Page number (default: 1)
 * - limit: Items per page (default: 50, max: 100)
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = request.nextUrl;

    // Extract and validate query params
    const q = searchParams.get("q") || undefined;
    const page = Math.max(1, parseInt(searchParams.get("page") || "1", 10));
    const limit = Math.min(100, Math.max(1, parseInt(searchParams.get("limit") || "50", 10)));

    // Build backend params
    const params: Record<string, string | number> = {
      page,
      limit,
    };
    if (q) {
      params.q = q;
    }

    // Call backend API
    const result = await serverApi.get<DomainUserListResponse>("/domain-users", {
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

    // Backend returns data in correct format (CamelModel)
    // Normalize to ensure consistent camelCase
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- Dynamic backend response normalization
    const data = result.data as any;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- Dynamic backend response normalization
    const normalizedItems = data.items.map((item: any) => ({
      id: item.id,
      username: item.username,
      fullName: item.fullName ?? item.full_name ?? null,
      title: item.title ?? null,
      office: item.office ?? null,
      phone: item.phone ?? null,
      manager: item.manager ?? null,
      createdAt: item.createdAt ?? item.created_at,
      updatedAt: item.updatedAt ?? item.updated_at,
    }));

    return NextResponse.json(
      {
        ok: true,
        data: {
          items: normalizedItems,
          total: data.total,
          page: data.page,
          limit: data.limit,
          hasMore: data.hasMore ?? data.has_more ?? false,
        },
      },
      { status: 200 }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("GET /api/domain-users error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to fetch domain users",
      },
      { status: 500 }
    );
  }
}
