/**
 * API Route: /api/admin/user-sources
 * Fetches available user source types with localized metadata
 */

import { NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

/**
 * User Source Metadata structure from backend
 */
interface UserSourceMetadata {
  code: string;
  nameEn: string;
  nameAr: string;
  descriptionEn: string;
  descriptionAr: string;
  icon: string;
  color: string;
  canOverride: boolean;
}

/**
 * GET /api/admin/user-sources
 * Fetch available user source types with localized metadata
 * No authentication required (public metadata)
 */
export async function GET() {
  try {
    // Forward to backend
    const result = await serverApi.get<UserSourceMetadata[]>(
      "/admin/user-sources",
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
    console.error("GET /api/admin/user-sources error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to fetch user sources",
      },
      { status: 500 }
    );
  }
}
