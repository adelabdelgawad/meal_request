/**
 * Minimal client-side session provider wrapper.
 *
 * This is the ONLY client component that wraps the app. It provides:
 * - A tiny session context (user + refresh function)
 * - Theme provider (dark/light mode)
 * - Language provider (en/ar with RTL support)
 * - Memoized context value (prevents unnecessary re-renders)
 *
 * The initial session is server-fetched and passed as a prop.
 * Client components use the useSession hook to access it.
 *
 * Key design:
 * - Minimal surface area
 * - Memoized value (useMemo prevents context thrashing)
 * - Focused on a single responsibility: app-wide providers
 */

'use client';

import React, { ReactNode, useMemo, useCallback, useState } from 'react';
import type { User } from '@/lib/auth/check-token';
import { ThemeProvider } from '@/components/theme-provider';
import { LanguageProvider } from '@/hooks/use-language';
import { NuqsAdapter } from 'nuqs/adapters/next/app';
import { Toaster } from '@/components/ui/sonner';

/**
 * Session context shape.
 */
export interface SessionContextType {
  user: User | null;
  refresh: () => Promise<void>;
  isRefreshing: boolean;
}

/**
 * React Context for session information.
 *
 * Access via useSession() hook (see lib/auth/use-session.ts).
 */
export const SessionContext = React.createContext<SessionContextType | undefined>(
  undefined
);

/**
 * Props for ClientAppWrapper.
 */
interface ClientAppWrapperProps {
  /**
   * Server-fetched initial session (or null if not authenticated).
   */
  initialSession: User | null;

  /**
   * Initial language preference (from cookie or default 'en').
   */
  initialLanguage?: 'en' | 'ar';

  /**
   * Child components to render.
   */
  children: ReactNode;
}

/**
 * Client-side wrapper that provides session, theme, and language context.
 *
 * This component is the ONLY top-level client provider in the app.
 * It receives the initial session from the server and provides it
 * to child components via React Context.
 *
 * Design rationale:
 * - Runs on client only (marked 'use client')
 * - Receives server-fetched session as a prop (no client-side fetch on mount)
 * - Provides context for useSession() hook
 * - Provides theme context via next-themes
 * - Provides language context with RTL support
 * - Memoizes context value to prevent unnecessary re-renders
 * - Provides refresh() function for manual session revalidation
 *
 * @param props - Wrapper props
 * @returns JSX.Element - Provider-wrapped children
 */
export default function ClientAppWrapper({
  initialSession,
  initialLanguage = 'en',
  children,
}: ClientAppWrapperProps) {
  // State for current user (starts with server session)
  const [user, setUser] = useState<User | null>(initialSession);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Refresh function: calls /api/auth/session to revalidate
  const refresh = useCallback(async () => {
    if (isRefreshing) return; // Prevent concurrent refreshes

    setIsRefreshing(true);
    try {
      const response = await fetch('/api/auth/session', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Include cookies
      });

      if (!response.ok) {
        // Session invalid, clear user
        setUser(null);
        return;
      }

      const data = await response.json();
      if (data.ok && data.user) {
        setUser(data.user);
      } else {
        // Session invalid, clear user
        setUser(null);
      }
    } catch (error) {
      console.error('Session refresh error:', error);
      // On network error, keep current user (optimistic)
      // They will be redirected on next protected page visit
    } finally {
      setIsRefreshing(false);
    }
  }, [isRefreshing]);

  // Memoize context value to prevent unnecessary re-renders
  // Only changes when user or refresh changes
  const contextValue = useMemo<SessionContextType>(
    () => ({
      user,
      refresh,
      isRefreshing,
    }),
    [user, refresh, isRefreshing]
  );

  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <SessionContext.Provider value={contextValue}>
        <LanguageProvider initialLanguage={initialLanguage}>
          <NuqsAdapter>
            {children}
          </NuqsAdapter>
          <Toaster position="top-center" richColors closeButton duration={5000} />
        </LanguageProvider>
      </SessionContext.Provider>
    </ThemeProvider>
  );
}
