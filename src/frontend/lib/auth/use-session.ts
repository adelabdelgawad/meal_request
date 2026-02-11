/**
 * Client-side hook for accessing session information.
 *
 * This hook consumes the session context provided by ClientAppWrapper.
 * It should be used in client components to access the current user session.
 *
 * Key features:
 * - No client-side fetch on mount (session comes from server)
 * - Provides status, user, and refresh function
 * - Minimal, focused API
 * - No loading states (session available immediately from server)
 */

'use client';

import { useContext } from 'react';
import { SessionContext } from '@/components/client-app-wrapper/client-app-wrapper';
import type { User } from './check-token';

/**
 * Status of the current session.
 */
export type SessionStatus = 'authenticated' | 'unauthenticated';

/**
 * Result from useSession hook.
 */
export interface UseSessionResult {
  /**
   * Current session status.
   * - 'authenticated': User is logged in (session.user is defined)
   * - 'unauthenticated': User is not logged in (session.user is null)
   */
  status: SessionStatus;

  /**
   * Current user information (null if not authenticated).
   */
  user: User | null;

  /**
   * Manually refresh the session from the server.
   *
   * Calls GET /api/auth/session to revalidate the user's session.
   * Useful after actions that might invalidate the session, or to
   * periodically check if the session is still valid.
   */
  refresh: () => Promise<void>;

  /**
   * Whether a refresh is currently in progress.
   */
  isRefreshing: boolean;
}

/**
 * Hook for accessing the current session in client components.
 *
 * Returns the user session from the context provided by ClientAppWrapper.
 * The initial session is server-fetched and passed as a prop, so there is
 * no loading state or client-side fetch on mount.
 *
 * Usage example:
 * ```tsx
 * 'use client';
 *
 * import { useSession } from '@/lib/auth/use-session';
 *
 * export function UserMenu() {
 *   const { status, user, refresh } = useSession();
 *
 *   if (status === 'unauthenticated') {
 *     return <LoginLink />;
 *   }
 *
 *   return (
 *     <div>
 *       <span>{user?.name}</span>
 *       <button onClick={refresh}>Refresh</button>
 *     </div>
 *   );
 * }
 * ```
 *
 * @returns UseSessionResult - Session information
 * @throws Error if hook is used outside of ClientAppWrapper context
 */
export function useSession(): UseSessionResult {
  const context = useContext(SessionContext);

  if (!context) {
    throw new Error(
      'useSession must be used within ClientAppWrapper. ' +
        'Ensure ClientAppWrapper is wrapping your app in layout.tsx'
    );
  }

  return {
    status: context.user ? 'authenticated' : 'unauthenticated',
    user: context.user,
    refresh: context.refresh,
    isRefreshing: context.isRefreshing,
  };
}

/**
 * Helper hook to check if the user is authenticated.
 *
 * Returns true if user is logged in, false otherwise.
 *
 * Usage:
 * ```tsx
 * const isAuthenticated = useIsAuthenticated();
 * if (!isAuthenticated) return <LoginPrompt />;
 * ```
 */
export function useIsAuthenticated(): boolean {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useIsAuthenticated must be used within ClientAppWrapper');
  }
  return !!context.user;
}

/**
 * Helper hook to check if user has a specific role.
 *
 * Returns true if user has the role, false otherwise.
 *
 * Usage:
 * ```tsx
 * const isAdmin = useHasRole('admin');
 * if (isAdmin) return <AdminPanel />;
 * ```
 */
export function useHasRole(role: string): boolean {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useHasRole must be used within ClientAppWrapper');
  }
  return !!(context.user?.roles?.includes(role));
}

/**
 * Helper hook to check if user has any of the specified roles.
 *
 * Returns true if user has at least one of the roles.
 *
 * Usage:
 * ```tsx
 * const isEditor = useHasAnyRole(['admin', 'editor']);
 * if (isEditor) return <EditorTools />;
 * ```
 */
export function useHasAnyRole(roles: string[]): boolean {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useHasAnyRole must be used within ClientAppWrapper');
  }
  return !!(context.user?.roles?.some((r) => roles.includes(r)));
}
