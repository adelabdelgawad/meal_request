/**
 * API Client with Automatic Token Refresh
 *
 * Features:
 * - Generic apiFetch<T>() for type-safe API calls
 * - Automatic Authorization header injection
 * - Automatic Accept-Language header based on locale cookie
 * - Concurrency-safe automatic token refresh on 401
 * - Support for stateful (cookie) and legacy (body) token modes
 * - Always includes credentials for cookie-based auth
 */

import type { TokenResponse } from '@/src/types/auth.types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';
const USE_STATEFUL_SESSIONS = process.env.NEXT_PUBLIC_USE_STATEFUL_SESSIONS === 'true';

// Token storage
let accessToken: string | null = null;
let refreshPromise: Promise<string> | null = null;

/**
 * Get current access token
 */
export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  if (!accessToken) {
    accessToken = localStorage.getItem('accessToken');
  }
  return accessToken;
}

/**
 * Set access token
 */
export function setAccessToken(token: string): void {
  if (typeof window === 'undefined') return;
  accessToken = token;
  localStorage.setItem('accessToken', token);
}

/**
 * Clear access token
 */
export function clearAccessToken(): void {
  if (typeof window === 'undefined') return;
  accessToken = null;
  localStorage.removeItem('accessToken');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('user');
}

/**
 * Get locale from cookie
 */
function getLocale(): string {
  if (typeof document === 'undefined') return 'en';
  const match = document.cookie.match(/locale=([^;]+)/);
  return match?.[1] || 'en';
}

/**
 * Refresh access token
 * Concurrency-safe: multiple simultaneous calls will share the same refresh promise
 */
export async function refreshAccessToken(): Promise<string> {
  // If refresh is already in progress, return the existing promise
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      let response: Response;

      if (USE_STATEFUL_SESSIONS) {
        // Stateful mode: refresh token is in HttpOnly cookie
        response = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
        });
      } else {
        // Legacy mode: refresh token in request body
        const refreshToken = typeof window !== 'undefined'
          ? localStorage.getItem('refreshToken')
          : null;

        if (!refreshToken) {
          throw new Error('No refresh token available');
        }

        response = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ refreshToken }),
        });
      }

      if (!response.ok) {
        // Refresh failed - clear tokens and redirect to login
        clearAccessToken();
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
        throw new Error('Token refresh failed');
      }

      const data = await response.json() as TokenResponse;
      setAccessToken(data.accessToken);
      return data.accessToken;
    } finally {
      // Always clear the promise when done (success or failure)
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/**
 * Generic fetch wrapper with automatic token refresh
 *
 * @template T - Expected response type
 * @param endpoint - API endpoint (without base URL)
 * @param options - Fetch options
 * @returns Parsed JSON response
 */
export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  // Prepare headers
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options.headers as Record<string, string>,
  };

  // Add Authorization header if token exists
  const token = getAccessToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Add Accept-Language header based on locale
  const locale = getLocale();
  if (locale === 'ar') {
    headers['Accept-Language'] = 'ar-EG,ar;q=0.9,en;q=0.8';
  } else {
    headers['Accept-Language'] = 'en-US,en;q=0.9,ar;q=0.8';
  }

  // Make request
  let response = await fetch(url, {
    ...options,
    credentials: 'include', // Always include cookies
    headers,
  });

  // Handle 401 - automatic token refresh
  // IMPORTANT: Don't attempt refresh on login/logout endpoints (401 = wrong credentials)
  const isAuthEndpoint = endpoint.includes('/auth/login') ||
                        endpoint.includes('/auth/logout') ||
                        endpoint.includes('/auth/refresh');

  if (response.status === 401 && !isAuthEndpoint) {
    try {
      const newAccessToken = await refreshAccessToken();

      // Retry with new token
      headers['Authorization'] = `Bearer ${newAccessToken}`;
      response = await fetch(url, {
        ...options,
        credentials: 'include',
        headers,
      });
    } catch (error) {
      // Refresh failed - redirect to login
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
      throw error;
    }
  }

  // Handle non-OK responses
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || errorData.message || `HTTP ${response.status}`);
  }

  return response.json();
}
