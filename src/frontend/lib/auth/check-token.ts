/**
 * Server-side token validation utility.
 *
 * This utility is designed to run on the server during page render or in server
 * components. It reads authentication tokens from HTTP-only cookies and validates
 * them against the backend validation endpoint.
 *
 * Key design decisions:
 * - Server-side only (uses cookies() from next/headers)
 * - Single backend call to POST /api/auth/validate
 * - No heavy dependencies
 * - Returns simple { ok, user, reason } result
 */

import { cookies } from "next/headers";

/**
 * Page information for navigation.
 */
export interface Page {
  id: number;
  name: string;
  description?: string;
  nameEn: string;
  nameAr: string;
  descriptionEn?: string;
  descriptionAr?: string;
  parentId?: number | null;
}

/**
 * User information returned from token validation.
 */
export interface User {
  id: string;
  name: string;
  username?: string;
  fullName?: string;
  title?: string;
  email?: string;
  roles?: string[];
  scopes?: string[];
  pages?: Page[];
  isSuperAdmin?: boolean;
  locale?: string;
  [key: string]: string | string[] | Page[] | boolean | undefined;
}

/**
 * Result of token validation.
 */
export interface CheckTokenResult {
  ok: boolean;
  user?: User;
  reason?: "invalid" | "network" | "unauthorized";
  /** True if a refresh token cookie exists (even if validation failed) */
  hasToken?: boolean;
}

/**
 * Validates an authentication token by calling the backend validation endpoint.
 *
 * This function runs on the server and should be called during page render or
 * in server components to check if a user is authenticated.
 *
 * Behavior:
 * 1. Reads authentication token from HTTP-only cookies
 * 2. Calls POST /api/auth/validate with the token
 * 3. Returns { ok: true, user } on success (2xx response)
 * 4. Returns { ok: false, reason } on failure or network error
 *
 * Common cookie names checked: 'auth-token', 'session', 'jwt'
 *
 * @returns Promise<CheckTokenResult> - Validation result with user info or error reason
 *
 * @example
 * // In a server component or page
 * const result = await checkToken();
 * if (!result.ok) {
 *   redirect('/auth/login');
 * }
 * // result.user is now available
 */
export async function checkToken(): Promise<CheckTokenResult> {
  try {
    // Get cookies from the request
    const cookieStore = await cookies();

    // Look for authentication token in cookies
    // Backend uses 'refresh' as the cookie name (SESSION_COOKIE_NAME in settings.py)
    const token =
      cookieStore.get("refresh")?.value ||
      cookieStore.get("refresh_token")?.value ||
      cookieStore.get("auth-token")?.value ||
      cookieStore.get("session")?.value ||
      cookieStore.get("jwt")?.value;

    // If no token found, return invalid
    if (!token) {
      return { ok: false, reason: "invalid", hasToken: false };
    }

    // We need to validate the token and get user data from the backend
    // This is necessary to get user information including pages for navigation
    try {
      const baseUrl = getBaseUrl();
      const meUrl = `${baseUrl}/api/auth/me`;

      // Call the /api/auth/me endpoint which handles refresh token → access token → session data
      // This endpoint reads the refresh token from cookies and returns full user data
      const response = await fetch(meUrl, {
        method: "GET",
        headers: {
          // Forward the cookie header with refresh token
          Cookie: `refresh=${token}`,
        },
        // Don't cache this request - always get fresh user data
        cache: "no-store",
      });

      if (!response.ok) {
        console.error(
          `[check-token] ❌ User data fetch failed with status: ${response.status}`
        );
        return { ok: false, reason: "unauthorized", hasToken: true };
      }

      const data = await response.json();

      if (!data.ok || !data.user) {
        return { ok: false, reason: "invalid", hasToken: true };
      }

      return {
        ok: true,
        user: data.user,
        hasToken: true,
      };
    } catch (error) {
      console.error("[check-token] ❌ User data fetch error:", error);
      return { ok: false, reason: "network", hasToken: true };
    }
  } catch (error) {
    // Network errors, timeouts, JSON parsing errors, etc.
    console.error("Token validation error:", error);
    return { ok: false, reason: "network", hasToken: false };
  }
}

/**
 * Get the base URL for Next.js API routes (not backend API).
 *
 * This function returns the URL for the Next.js frontend server,
 * which hosts the /api/auth/* routes.
 *
 * Note: Do NOT use NEXT_PUBLIC_API_URL here as that points to the backend.
 */
function getBaseUrl(): string {
  // Production (Vercel)
  if (process.env.VERCEL_URL) {
    return `https://${process.env.VERCEL_URL}`;
  }

  // Custom site URL (Docker, staging, etc.)
  if (process.env.SITE_URL) {
    return process.env.SITE_URL;
  }

  // Development: Next.js runs on port 3000
  // Use 127.0.0.1 instead of localhost for better Docker compatibility
  return "http://127.0.0.1:3000";
}

/**
 * Helper to determine if a refresh token is likely present.
 *
 * This does a lightweight check (presence only, no validation).
 * Useful for rendering navigation without blocking on backend validation.
 *
 * @returns boolean - True if a refresh token cookie exists
 */
export async function isTokenPresent(): Promise<boolean> {
  const cookieStore = await cookies();
  return !!(
    cookieStore.get("refresh")?.value ||
    cookieStore.get("refresh_token")?.value ||
    cookieStore.get("auth-token")?.value ||
    cookieStore.get("session")?.value ||
    cookieStore.get("jwt")?.value
  );
}
