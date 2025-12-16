/**
 * Next.js proxy for authentication (formerly middleware.ts).
 *
 * This proxy provides lightweight route protection by checking for a valid
 * authentication token before allowing access to protected routes.
 *
 * Note: Proxy runs on the Node.js runtime at the network boundary.
 * Use sparingly for critical routes. For most pages, prefer the RequireAuth
 * server component wrapper instead.
 *
 * To enable/disable: Set NEXT_PUBLIC_AUTH_PROXY_ENABLED=true in .env.local
 */

import { NextRequest, NextResponse } from 'next/server';

/**
 * Routes that require authentication.
 * Users without a valid token will be redirected to /auth/login.
 */
const PROTECTED_ROUTES = [
  /^\/(?!auth\/|api\/)/, // Everything except /auth/* and /api/*
];

/**
 * Routes that should never be protected (always accessible).
 */
const PUBLIC_ROUTES = [
  /^\/auth\//,
  /^\/api\/auth\/login$/,
  /^\/api\/auth\/domains$/,
  /^\/public\//,
];

/**
 * Check if a route is protected.
 */
function isProtectedRoute(pathname: string): boolean {
  // Allow public routes
  if (PUBLIC_ROUTES.some((route) => route.test(pathname))) {
    return false;
  }

  // Check if it matches any protected route pattern
  return PROTECTED_ROUTES.some((route) => route.test(pathname));
}

/**
 * Extract authentication token from request.
 * Checks multiple possible cookie names and authorization header.
 */
function getTokenFromRequest(request: NextRequest): string | undefined {
  // Try to get token from cookies (most common for HTTP-only cookies)
  const token =
    request.cookies.get('auth-token')?.value ||
    request.cookies.get('session')?.value ||
    request.cookies.get('jwt')?.value;

  if (token) {
    return token;
  }

  // Try to get token from Authorization header (Bearer token)
  const authHeader = request.headers.get('authorization');
  if (authHeader?.startsWith('Bearer ')) {
    return authHeader.slice(7);
  }

  return undefined;
}

/**
 * Proxy function that checks authentication on protected routes.
 */
export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Check if proxy is enabled
  const proxyEnabled =
    process.env.NEXT_PUBLIC_AUTH_PROXY_ENABLED === 'true';

  if (!proxyEnabled) {
    return NextResponse.next();
  }

  // Skip protected route check for non-protected routes
  if (!isProtectedRoute(pathname)) {
    return NextResponse.next();
  }

  // Get token from request
  const token = getTokenFromRequest(request);

  // If no token, redirect to login
  if (!token) {
    const loginUrl = new URL('/auth/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Token exists, allow request to proceed
  // Note: Full validation happens on the server via RequireAuth wrapper
  // Proxy only does lightweight token presence check to avoid latency
  return NextResponse.next();
}

/**
 * Configure which routes should trigger the proxy.
 * This is important for performance - only run proxy where needed.
 */
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public (public files)
     */
    '/((?!api|_next/static|_next/image|favicon.ico|public).*)',
  ],
};
