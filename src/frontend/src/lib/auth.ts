/**
 * Authentication Module
 *
 * Centralized auth operations:
 * - login() - Login with username/password
 * - logout() - Logout and revoke tokens
 * - getSession() - Validate current session
 * - isAuthenticated() - Check if user is logged in
 */

import { apiFetch, setAccessToken, clearAccessToken } from './api-client';
import type { LoginRequest, LoginResponse, SessionResponse, UserInfo } from '@/src/types/auth.types';

const USE_STATEFUL_SESSIONS = process.env.NEXT_PUBLIC_USE_STATEFUL_SESSIONS === 'true';

/**
 * Login with username and password
 */
export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  const response = await apiFetch<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });

  // Store access token
  setAccessToken(response.accessToken);

  // Store refresh token (only in legacy mode)
  if (response.refreshToken && !USE_STATEFUL_SESSIONS) {
    localStorage.setItem('refreshToken', response.refreshToken);
  }

  // Store user info
  localStorage.setItem('user', JSON.stringify(response.user));

  return response;
}

/**
 * Logout and revoke tokens
 */
export async function logout(): Promise<void> {
  try {
    if (USE_STATEFUL_SESSIONS) {
      // Stateful mode: cookie sent automatically
      await apiFetch('/auth/logout', {
        method: 'POST',
      });
    } else {
      // Legacy mode: send refresh token in body
      const refreshToken = localStorage.getItem('refreshToken');
      await apiFetch('/auth/logout', {
        method: 'POST',
        body: JSON.stringify({ token: refreshToken }),
      });
    }
  } catch (error) {
    console.error('Logout error:', error);
  } finally {
    // Always clear tokens and redirect
    clearAccessToken();
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  }
}

/**
 * Get current session
 */
export async function getSession(): Promise<SessionResponse> {
  return apiFetch<SessionResponse>('/auth/session');
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  if (typeof window === 'undefined') return false;
  return !!localStorage.getItem('accessToken');
}

/**
 * Get current user from localStorage
 */
export function getUser(): UserInfo | null {
  if (typeof window === 'undefined') return null;
  const userStr = localStorage.getItem('user');
  if (!userStr) return null;
  try {
    return JSON.parse(userStr);
  } catch {
    return null;
  }
}
