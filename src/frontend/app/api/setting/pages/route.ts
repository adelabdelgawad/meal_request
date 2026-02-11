/**
 * API Route: /api/setting/pages
 * Handles pages CRUD operations
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";
import type { SettingPagesResponse, PageResponse } from "@/types/pages";

/**
 * GET /api/setting/pages
 * Fetch all pages with optional filters
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);

    // Build query parameters
    const queryParams = new URLSearchParams();
    const limit = searchParams.get("limit") || "1000";
    const skip = searchParams.get("skip") || "0";
    const isActive = searchParams.get("is_active");
    const pageName = searchParams.get("page_name");

    queryParams.append("limit", limit);
    queryParams.append("skip", skip);
    if (isActive !== null) {
      queryParams.append("is_active", isActive);
    }
    if (pageName !== null) {
      queryParams.append("page_name", pageName);
    }

    const queryString = queryParams.toString();
    const url = `/admin/pages${queryString ? `?${queryString}` : ""}`;

    const result = await serverApi.get<SettingPagesResponse>(url, {
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
    console.error("GET /api/setting/pages error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to fetch pages",
      },
      { status: 500 }
    );
  }
}

/**
 * POST /api/setting/pages
 * Create a new page
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

    const result = await serverApi.post<PageResponse>("/admin/pages", body, {
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
    console.error("POST /api/setting/pages error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to create page",
      },
      { status: 500 }
    );
  }
}
