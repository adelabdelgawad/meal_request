/**
 * API Route: POST /api/auth/refresh
 *
 * Refreshes the access token using the refresh token stored in HttpOnly cookie.
 * The refresh token is automatically sent via cookies and rotated by the backend.
 *
 * This endpoint is called automatically by the token manager before token expiry.
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

interface RefreshResponse {
  accessToken: string;
  tokenType: string;
  expiresIn: number;
}

/**
 * POST /api/auth/refresh
 *
 * Forwards refresh request to backend.
 * The refresh token is automatically sent via HttpOnly cookie.
 * Backend rotates the refresh token and returns a new access token.
 */
export async function POST(request: NextRequest) {
  try {
    // Call backend refresh endpoint
    // Refresh token is automatically sent via HttpOnly cookie
    // No body needed for stateful sessions
    const result = await serverApi.post<RefreshResponse>(
      "/api/v1/auth/refresh",
      {}, // Empty body - refresh token is in cookie
      {
        credentials: "include", // Important: send cookies
        headers: {
          // Forward cookies from client request to backend
          ...(request.headers.get("cookie") && {
            cookie: request.headers.get("cookie") || "",
          }),
        },
      }
    );

    // If backend request failed, return the error
    if (!result.ok) {
      return NextResponse.json(
        {
          ok: false,
          error: result.error,
          message: result.message || "Token refresh failed",
        },
        { status: result.status || 401 }
      );
    }

    // Success! Return new access token
    // The backend has rotated the refresh cookie
    return NextResponse.json(
      {
        ok: true,
        message: "Token refreshed successfully",
        data: result.data,
      },
      { status: 200 }
    );
  } catch (error) {
    // Handle unexpected errors
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("Refresh endpoint error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Token refresh service unavailable. Please try again.",
      },
      { status: 503 }
    );
  }
}

/**
 * Handle other HTTP methods
 */
export function GET() {
  return NextResponse.json(
    { error: "Method not allowed", message: "Use POST /api/auth/refresh" },
    { status: 405 }
  );
}
