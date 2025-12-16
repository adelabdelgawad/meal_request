/**
 * Helper functions for authentication proxy (formerly middleware).
 *
 * This module provides lightweight functions that proxy can use to check
 * for authentication without making remote validation calls.
 *
 * Why lightweight checks in proxy?
 * - Proxy runs on every request (latency impact)
 * - Remote validation adds network round-trip time
 * - Better to do a fast presence check + full validation on server components
 *
 * Pattern:
 * - Proxy: check token presence (cookie exists)
 * - Server components: validate token fully via checkToken()
 */

import { NextRequest } from 'next/server';

/**
 * Extract authentication token from proxy request.
 *
 * This function checks multiple possible locations:
 * - HTTP-only cookies (auth-token, session, jwt)
 * - Authorization header (Bearer token)
 *
 * @param request - Next.js proxy request
 * @returns Token string if found, undefined otherwise
 */
export function getTokenFromRequest(request: NextRequest): string | undefined {
  // Check cookies (most common for HTTP-only cookies)
  const cookieHeader = request.headers.get('cookie');

  if (cookieHeader) {
    // Simple cookie parsing for auth tokens
    const authTokenMatch = cookieHeader.match(/auth-token=([^;]+)/);
    if (authTokenMatch) return authTokenMatch[1];

    const sessionMatch = cookieHeader.match(/session=([^;]+)/);
    if (sessionMatch) return sessionMatch[1];

    const jwtMatch = cookieHeader.match(/jwt=([^;]+)/);
    if (jwtMatch) return jwtMatch[1];
  }

  // Check Authorization header (Bearer token)
  const authHeader = request.headers.get('authorization');
  if (authHeader?.startsWith('Bearer ')) {
    return authHeader.slice(7);
  }

  return undefined;
}

/**
 * Check if a token is likely present (lightweight check).
 *
 * This does NOT validate the token. It only checks for presence and basic
 * structure. Use this for proxy to avoid expensive validation.
 *
 * @param token - Token string to check
 * @returns boolean - True if token looks present and valid
 */
export function isTokenLikelyValid(token?: string): boolean {
  if (!token) return false;
  // Very basic check: token should be a non-empty string
  // Real validation happens on the server via checkToken()
  return token.length > 10; // JWT tokens are longer than 10 chars
}

/**
 * Protected routes that require authentication.
 *
 * These patterns match routes that should require authentication.
 * Routes not matching these patterns will be allowed without auth.
 */
export const PROTECTED_ROUTES = [
  // Examples - customize based on your app:
  /^\/app\//,  // Everything under /app/
  /^\/dashboard/,
  /^\/settings/,
  /^\/profile/,
];

/**
 * Public routes that never require authentication.
 *
 * These routes are always accessible, even without a token.
 */
export const PUBLIC_ROUTES = [
  /^\/auth\//,  // Auth pages
  /^\/public\//,
  /^\/api\/auth\//,  // Auth API endpoints
  /^\/$/, // Home page
];

/**
 * Check if a route should require authentication.
 *
 * @param pathname - Request pathname
 * @returns boolean - True if route requires authentication
 */
export function isProtectedRoute(pathname: string): boolean {
  // Check public routes first
  if (PUBLIC_ROUTES.some((route) => route.test(pathname))) {
    return false;
  }

  // Check protected routes
  return PROTECTED_ROUTES.some((route) => route.test(pathname));
}
