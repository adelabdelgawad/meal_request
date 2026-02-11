/**
 * API Route: POST /api/auth/locale
 *
 * Updates user's locale preference in the database.
 * Proxies request to backend /api/v1/me/locale endpoint.
 *
 * The backend:
 * 1. Updates the user's preferred_locale in the database
 * 2. Sets a locale cookie for the response
 *
 * After calling this endpoint, the client should refresh the session
 * to get the updated user data with the new locale.
 */

import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";

interface LocaleRequest {
  locale: string;
}

interface LocaleResponse {
  message: string;
  locale: string;
}


/**
 * Validate locale request body
 */
function validateLocaleRequest(body: unknown): { valid: boolean; error?: string; data?: LocaleRequest } {
  if (!body || typeof body !== "object") {
    return { valid: false, error: "Invalid request body" };
  }

  const data = body as Record<string, unknown>;

  if (typeof data.locale !== "string" || data.locale.trim().length === 0) {
    return { valid: false, error: "Locale is required" };
  }

  const locale = data.locale.trim().toLowerCase();
  if (!["en", "ar"].includes(locale)) {
    return { valid: false, error: "Invalid locale. Supported: en, ar" };
  }

  return {
    valid: true,
    data: {
      locale,
    },
  };
}

/**
 * POST /api/auth/locale
 *
 * Updates user's locale preference by forwarding to backend.
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

    // Validate locale request
    const validation = validateLocaleRequest(body);
    if (!validation.valid || !validation.data) {
      return NextResponse.json(
        { ok: false, error: "validation_error", message: validation.error },
        { status: 400 }
      );
    }

    // Check for refresh token cookie (stateful sessions)
    const refreshToken = request.cookies.get("refresh")?.value;
    if (!refreshToken) {
      return NextResponse.json(
        { ok: false, error: "unauthorized", message: "No session found" },
        { status: 401 }
      );
    }

    // Get cookie header to forward to backend
    const cookieHeader = request.headers.get("cookie");


    // Call backend /api/v1/me/locale endpoint
    // Forward cookies so backend can validate the session via refresh token
    const result = await serverApi.post<LocaleResponse>(
      "/api/v1/me/locale",
      validation.data,
      {
        headers: {
          ...(cookieHeader && { Cookie: cookieHeader }),
        },
      }
    );

    // If backend request failed, return the error
    if (!result.ok) {
      console.error(`[locale-route] Failed to update locale:`, result);
      return NextResponse.json(
        {
          ok: false,
          error: "error" in result ? result.error : "unknown_error",
          message: result.message || "Failed to update locale",
        },
        { status: result.status }
      );
    }

    // Success - create response
    const responseData = "data" in result ? result.data : null;

    const response = NextResponse.json(
      {
        ok: true,
        message: responseData?.message || "Locale updated successfully",
        locale: validation.data.locale,
      },
      { status: 200 }
    );

    // Forward Set-Cookie header from backend if present (locale cookie)
    if (result.headers && result.headers["set-cookie"]) {
      response.headers.set("Set-Cookie", result.headers["set-cookie"]);
    }

    return response;
  } catch (error) {
    // Handle unexpected errors
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("[locale-route] Error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to update locale preference",
      },
      { status: 500 }
    );
  }
}

/**
 * GET /api/auth/locale
 *
 * Gets user's current locale from JWT refresh token (zero DB queries).
 * Proxies to backend /api/v1/me/locale endpoint.
 */
export async function GET(request: NextRequest) {
  try {
    // Check for refresh token cookie (stateful sessions)
    const refreshToken = request.cookies.get("refresh")?.value;
    if (!refreshToken) {
      return NextResponse.json(
        { ok: false, error: "unauthorized", message: "No session found" },
        { status: 401 }
      );
    }

    // Get cookie header to forward to backend
    const cookieHeader = request.headers.get("cookie");


    // Call backend /api/v1/me/locale endpoint
    const result = await serverApi.get<{ locale: string }>(
      "/api/v1/me/locale",
      {
        headers: {
          ...(cookieHeader && { Cookie: cookieHeader }),
        },
      }
    );

    // If backend request failed, return the error
    if (!result.ok) {
      console.error(`[locale-route GET] Failed to fetch locale:`, result);
      return NextResponse.json(
        {
          ok: false,
          error: "error" in result ? result.error : "unknown_error",
          message: result.message || "Failed to fetch locale",
        },
        { status: result.status }
      );
    }

    // Success
    const responseData = "data" in result ? result.data : null;

    return NextResponse.json(
      {
        ok: true,
        locale: responseData?.locale || "en",
      },
      { status: 200 }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("[locale-route GET] Error:", errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: "server_error",
        message: "Failed to fetch locale",
      },
      { status: 500 }
    );
  }
}
