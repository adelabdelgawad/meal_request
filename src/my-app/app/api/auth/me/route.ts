/**
 * API Route: GET /api/auth/me
 *
 * Returns current user information based on refresh token cookie.
 * Used by server components to get user data during SSR.
 *
 * This endpoint:
 * 1. Reads refresh token from cookies
 * 2. Calls backend /validate endpoint (does NOT rotate tokens)
 * 3. Returns user data with pages
 *
 * NOTE: This uses /validate instead of /refresh to avoid token rotation
 * during SSR where multiple parallel requests can occur.
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

interface UserResponse {
  id: string;
  username: string;
  roles: string[];
  scopes: string[];
  pages: Array<{
    id: number;
    name: string;
    description?: string;
    nameEn: string;
    nameAr: string;
    descriptionEn?: string;
    descriptionAr?: string;
  }>;
  isSuperAdmin: boolean;
  locale: string;
}

interface ValidateResponse {
  ok: boolean;
  user: UserResponse;
}

/**
 * GET /api/auth/me
 *
 * Returns current user data by validating refresh token (no rotation).
 */
export async function GET(request: NextRequest) {
  try {
    // Get refresh token from cookies
    const refreshToken = request.cookies.get("refresh")?.value;

    if (!refreshToken) {
      return NextResponse.json(
        { ok: false, error: "no_token", message: "No refresh token found" },
        { status: 401 }
      );
    }

    // Get cookie header to forward to backend
    const cookieHeader = request.headers.get("cookie");

    // Call /validate endpoint - validates refresh token WITHOUT rotating
    // This is safe for parallel SSR requests
    const validateResult = await serverApi.get<ValidateResponse>(
      "/api/v1/auth/validate",
      {
        headers: {
          ...(cookieHeader && { Cookie: cookieHeader }),
        },
      }
    );

    const userData = validateResult.ok && 'data' in validateResult ? validateResult.data?.user : undefined;

    if (!validateResult.ok || !userData) {
      const errorDetails = 'error' in validateResult ? validateResult.error : undefined;
      return NextResponse.json(
        { ok: false, error: "validation_failed", message: "Failed to validate session", details: errorDetails },
        { status: 401 }
      );
    }

    // Return user data
    return NextResponse.json(
      {
        ok: true,
        user: userData,
      },
      { status: 200 }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("[me-route] Error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to get user data",
      },
      { status: 500 }
    );
  }
}
