/**
 * API Route: POST /api/auth/login
 *
 * Handles user login by forwarding credentials to the backend.
 * The backend automatically:
 * - Determines if this is a local admin login or domain (LDAP) authentication
 * - Sets the refresh token as HttpOnly cookie
 * - Returns access token in response body
 *
 * Uses the server-side Axios connector for consistent error handling and timeouts.
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

/**
 * Login request validation
 */
interface LoginRequest {
  username: string;
  password: string;
}

/**
 * Validate login request body
 */
function validateLoginRequest(body: unknown): { valid: boolean; error?: string; data?: LoginRequest } {
  if (!body || typeof body !== "object") {
    return { valid: false, error: "Invalid request body" };
  }

  const data = body as Record<string, unknown>;

  if (typeof data.username !== "string" || data.username.trim().length === 0) {
    return { valid: false, error: "Username is required" };
  }

  if (typeof data.password !== "string" || data.password.length === 0) {
    return { valid: false, error: "Password is required" };
  }

  return {
    valid: true,
    data: {
      username: data.username.trim(),
      password: data.password,
    },
  };
}

/**
 * POST /api/auth/login
 *
 * Forwards login request to backend via server-side Axios connector.
 * Backend sets refresh token cookie directly (stateful sessions).
 */
export async function POST(request: NextRequest) {
  try {
    // Parse request body
    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { ok: false, error: "invalid_json", message: "Request body must be valid JSON" },
        { status: 400 }
      );
    }

    // Validate login request
    const validation = validateLoginRequest(body);
    if (!validation.valid) {
      return NextResponse.json(
        { ok: false, error: "validation_error", message: validation.error },
        { status: 400 }
      );
    }

    // Call backend via server Axios connector
    // Backend endpoint: /api/v1/auth/login
    // The backend will set the refresh cookie directly in its response

    const result = await serverApi.post<Record<string, unknown>>(
      "/api/v1/auth/login",
      validation.data,
      {
        // Pass through cookies from backend to client
        credentials: "include",
      }
    );


    // If backend request failed, return the error
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

    // Success! Return user data and access token

    const response = NextResponse.json(
      {
        ok: true,
        message: "Login successful",
        data: result.data,
      },
      { status: 200 }
    );

    // CRITICAL: Forward Set-Cookie header from backend to browser
    // The backend sets the refresh token as HttpOnly cookie
    // We need to pass it through to the client
    if (result.headers && result.headers["set-cookie"]) {
      response.headers.set("Set-Cookie", result.headers["set-cookie"]);
    } else {
    }

    return response;
  } catch (error) {
    // Handle unexpected errors
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("Login endpoint error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Login service unavailable. Please try again.",
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
    { error: "Method not allowed", message: "Use POST /api/auth/login" },
    { status: 405 }
  );
}
