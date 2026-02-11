/**
 * Server-side authentication wrapper for protecting pages.
 *
 * This component enforces authentication on the server before rendering any
 * protected content. It uses Next.js server components and the redirect function
 * to ensure unauthenticated users never receive protected HTML.
 *
 * Key benefits:
 * - No HTML is sent to unauthenticated users
 * - Redirect happens before hydration (no client-side redirect flicker)
 * - Full validation happens on the server
 * - Works without JavaScript
 */

import { redirect } from 'next/navigation';
import { ReactNode } from 'react';
import { checkToken, type User } from './check-token';

/**
 * Props for the RequireAuth wrapper component.
 */
interface RequireAuthProps {
  /**
   * Child components to render if authentication succeeds.
   */
  children: ReactNode;

  /**
   * Optional redirect destination if authentication fails.
   * Defaults to '/login' (route group (auth) doesn't appear in URL).
   */
  redirectTo?: string;

  /**
   * Optional callback to execute before redirect on auth failure.
   * Useful for logging or cleanup. Cannot be async (runs in return phase).
   */
  onAuthFailure?: (reason?: string) => void;
}

/**
 * Server component wrapper that enforces authentication on protected pages.
 *
 * This component must be used only in server components (not client components).
 * It checks authentication on the server during page render. If the user is not
 * authenticated, it redirects to the login page before any HTML is sent to the browser.
 *
 * Usage in a server page component:
 * ```tsx
 * // app/(app)/dashboard/page.tsx (server component)
 * import RequireAuth from '@/lib/auth/require-auth';
 *
 * export default function DashboardPage() {
 *   return (
 *     <RequireAuth redirectTo="/login">
 *       <main>
 *         <h1>Dashboard</h1>
 *         <p>This content is protected.</p>
 *       </main>
 *     </RequireAuth>
 *   );
 * }
 * ```
 *
 * How it works:
 * 1. Runs on the server during page render
 * 2. Calls checkToken() to validate the user's authentication token
 * 3. If valid, renders children
 * 4. If invalid, optionally calls onAuthFailure callback, then redirects to login page
 *
 * Important: The redirect happens BEFORE React hydration, so the user never
 * sees the protected page in the browser.
 *
 * @param props - Component props
 * @returns JSX.Element if authenticated, never returns if not authenticated (redirects)
 */
export default async function RequireAuth({
  children,
  redirectTo = '/login',
  onAuthFailure,
}: RequireAuthProps) {
  // Validate token on the server
  const result = await checkToken();

  // If validation failed, redirect to login
  if (!result.ok) {
    // Call optional failure callback for logging/analytics
    if (onAuthFailure) {
      onAuthFailure(result.reason);
    }

    // Redirect before rendering any protected content
    // This happens on the server, before hydration
    redirect(redirectTo);
  }

  // Authentication successful, render protected content
  return <>{children}</>;
}

/**
 * Variant: RequireAuthWithRole - checks both authentication and user role.
 *
 * Protects pages to only authenticated users with a specific role.
 *
 * Usage:
 * ```tsx
 * import RequireAuthWithRole from '@/lib/auth/require-auth';
 *
 * export default function AdminPage() {
 *   return (
 *     <RequireAuthWithRole
 *       role="admin"
 *       redirectTo="/unauthorized"
 *     >
 *       <AdminPanel />
 *     </RequireAuthWithRole>
 *   );
 * }
 * ```
 */
interface RequireAuthWithRoleProps extends RequireAuthProps {
  /**
   * Required role for access.
   */
  role: string;
}

export async function RequireAuthWithRole({
  children,
  role,
  redirectTo = '/login',
  onAuthFailure,
}: RequireAuthWithRoleProps) {
  // Check authentication
  const result = await checkToken();

  if (!result.ok) {
    if (onAuthFailure) {
      onAuthFailure(result.reason);
    }
    redirect(redirectTo);
  }

  // Check role
  if (!result.user?.roles?.includes(role)) {
    if (onAuthFailure) {
      onAuthFailure('insufficient_permissions');
    }
    redirect('/unauthorized');
  }

  // Both authentication and role check passed
  return <>{children}</>;
}

/**
 * Variant: RequireAuthWithCallback - allows custom auth handling.
 *
 * Useful when you need custom permission checks or conditional logic.
 *
 * Usage:
 * ```tsx
 * <RequireAuthWithCallback
 *   shouldAllow={(user) => user.email.endsWith('@company.com')}
 *   deniedPath="/access-denied"
 * >
 *   <CompanyContent />
 * </RequireAuthWithCallback>
 * ```
 */
interface RequireAuthWithCallbackProps extends RequireAuthProps {
  /**
   * Custom permission check function.
   */
  shouldAllow: (user: User) => boolean;

  /**
   * Path to redirect to if shouldAllow returns false.
   */
  deniedPath: string;
}

export async function RequireAuthWithCallback({
  children,
  shouldAllow,
  deniedPath,
  redirectTo = '/login',
  onAuthFailure,
}: RequireAuthWithCallbackProps) {
  // Check authentication
  const result = await checkToken();

  if (!result.ok) {
    if (onAuthFailure) {
      onAuthFailure(result.reason);
    }
    redirect(redirectTo);
  }

  // Check custom permission
  if (result.user && !shouldAllow(result.user)) {
    if (onAuthFailure) {
      onAuthFailure('permission_denied');
    }
    redirect(deniedPath);
  }

  return <>{children}</>;
}
