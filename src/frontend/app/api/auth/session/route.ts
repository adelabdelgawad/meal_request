/**
 * API Route: GET /api/auth/session
 *
 * Validates the current user's session and returns their user data.
 * Called by the useSession() hook to refresh/revalidate the session.
 *
 * Uses stateful sessions with refresh token cookie.
 * Calls backend /validate endpoint to check session without rotating tokens.
 *
 * Response on success (200):
 * {
 *   "ok": true,
 *   "user": {
 *     "id": "string",
 *     "username": "string",
 *     "roles": ["string"],
 *     "scopes": ["string"],
 *     "pages": [{"id": number, "name": "string"}]
 *   }
 * }
 *
 * Response on failure (401):
 * {
 *   "ok": false,
 *   "error": "unauthorized",
 *   "message": "Session invalid or expired"
 * }
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
    parentId?: number;
  }>;
  isSuperAdmin: boolean;
  locale: string;
  fullName?: string;
  title?: string;
}

interface ValidateResponse {
  ok: boolean;
  user: UserResponse;
}

/**
 * GET /api/auth/session
 *
 * Validates the current user's session using refresh token cookie.
 * This is used by the session context to refresh user data.
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
    // This is safe for parallel SSR requests and client-side refresh calls
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
    console.error("[session-route] Error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to validate session",
      },
      { status: 500 }
    );
  }
}

/**
 * Handle POST and other methods
 */
export function POST() {
  return NextResponse.json(
    { error: "Method not allowed", message: "Use GET /api/auth/session" },
    { status: 405 }
  );
}
