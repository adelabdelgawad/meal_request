/**
 * API Route: POST /api/auth/logout
 *
 * Handles user logout by revoking the session on the backend.
 * The refresh token is automatically sent via HttpOnly cookie.
 * Backend revokes the session in database and clears the refresh cookie.
 *
 * Response on success (200):
 * {
 *   "ok": true,
 *   "message": "Logged out successfully"
 * }
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

interface LogoutResponse {
  message: string;
  ok: boolean;
}

/**
 * POST /api/auth/logout
 *
 * Forwards logout request to backend.
 * The refresh token is automatically sent via HttpOnly cookie.
 * Backend revokes the session and clears cookies.
 */
export async function POST(request: NextRequest) {
  try {
    // Get cookies from the incoming request
    const cookieHeader = request.headers.get("cookie");

    // Call backend logout endpoint via serverApi
    // Forward cookies so backend can identify the session
    const result = await serverApi.post<LogoutResponse>(
      "/api/v1/auth/logout",
      {}, // Empty body
      {
        headers: {
          // Forward all cookies to backend
          ...(cookieHeader && { Cookie: cookieHeader }),
        },
      }
    );

    const responseMessage = result.ok && 'data' in result ? result.data?.message : undefined;

    // Create response
    const response = NextResponse.json(
      {
        ok: true,
        message: responseMessage || "Logged out successfully",
      },
      { status: 200 }
    );

    // CRITICAL: Forward Set-Cookie header from backend to clear the refresh cookie
    // Note: Set-Cookie can be an array or a string
    const setCookieHeader = result.headers?.["set-cookie"];

    if (setCookieHeader) {
      // If it's an array, we need to handle it properly
      // NextResponse doesn't support multiple Set-Cookie headers via headers.set()
      // We need to manually set the cookies instead

      // Parse and manually clear the refresh cookie
      // CRITICAL: Must match the EXACT settings used when the cookie was set
      // Backend uses: Secure=true, SameSite=strict (from settings.py)
      response.cookies.set("refresh", "", {
        httpOnly: true,
        secure: true, // MUST match backend (SESSION_COOKIE_SECURE=true)
        sameSite: "strict", // MUST match backend (SESSION_COOKIE_SAMESITE=strict)
        maxAge: 0,
        path: "/",
      });

    } else {
      // Manually clear cookies if backend didn't send Set-Cookie header

      // Clear refresh cookie (primary session cookie)
      // MUST match backend settings exactly
      response.cookies.set("refresh", "", {
        httpOnly: true,
        secure: true, // Backend default
        sameSite: "strict", // Backend default
        maxAge: 0,
        path: "/",
      });

      // Clear locale cookie
      response.cookies.set("locale", "", {
        httpOnly: false,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        maxAge: 0,
        path: "/",
      });
    }

    // Also clear any legacy cookies
    response.cookies.set("access_token", "", { maxAge: 0, path: "/" });
    response.cookies.set("refresh_token", "", { maxAge: 0, path: "/" });

    return response;
  } catch (error) {
    // Handle unexpected errors (network errors, backend unreachable, timeout, etc.)
    // CRITICAL: Even if backend is unreachable, we MUST log the user out on the frontend
    // The session will remain in the backend database, but the user won't be able to use it
    // because we're clearing the cookie that contains the refresh token
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    const errorName = error instanceof Error ? error.name : "UnknownError";

    console.error("[logout-route] ❌ Backend unreachable or error during logout:");
    console.error(`[logout-route] Error name: ${errorName}`);
    console.error(`[logout-route] Error message: ${errorMessage}`);
    console.error("[logout-route] ⚠️ Performing client-side logout (clearing cookies)");

    // Check if it's a network/timeout error
    const isNetworkError =
      errorName === "AbortError" ||
      errorName === "TimeoutError" ||
      errorMessage.includes("ECONNREFUSED") ||
      errorMessage.includes("ETIMEDOUT") ||
      errorMessage.includes("Network Error");

    // Always return success to allow client-side cleanup
    // This ensures the user is logged out on the frontend even if backend fails
    const response = NextResponse.json(
      {
        ok: true, // Return success to allow redirect
        message: isNetworkError
          ? "Logged out locally (backend unreachable)"
          : "Logged out (local cleanup)",
        warning: isNetworkError
          ? "Backend was unreachable. Your session will expire naturally."
          : undefined,
      },
      { status: 200 }
    );

    // Clear all cookies - MOST IMPORTANT STEP
    // Without these cookies, the user cannot authenticate anymore
    // MUST match backend settings exactly
    response.cookies.set("refresh", "", {
      httpOnly: true,
      secure: true, // Backend default
      sameSite: "strict", // Backend default
      maxAge: 0,
      path: "/",
    });

    response.cookies.set("locale", "", {
      httpOnly: false,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 0,
      path: "/",
    });

    response.cookies.set("access_token", "", { maxAge: 0, path: "/" });
    response.cookies.set("refresh_token", "", { maxAge: 0, path: "/" });

    return response;
  }
}

/**
 * Handle other HTTP methods
 */
export function GET() {
  return NextResponse.json(
    { error: "Method not allowed", message: "Use POST /api/auth/logout" },
    { status: 405 }
  );
}
