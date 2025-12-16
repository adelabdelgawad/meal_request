/**
 * Token Manager - Stateful Session Support (Cookie-Based)
 *
 * Updated for stateful sessions where:
 * - Access tokens stored in memory (short-lived, 15 min)
 * - Refresh tokens stored in HttpOnly cookies by backend (long-lived, 30 days)
 * - Automatic token refresh before expiration
 */

import { serverApi } from "@/lib/http/axios-server";

export interface TokenData {
  accessToken: string;
  expiresIn: number; // seconds
  tokenType: string;
  // No refreshToken - it's in HttpOnly cookie managed by backend
}

export interface UserSession {
  id: string;
  username: string;
  roles: string[];
  scopes: string[];
  pages: Array<{ id: number; name: string }>;
}

/**
 * Token refresh response from backend
 */
interface TokenRefreshResponse {
  accessToken: string;
  tokenType: string;
  expiresIn: number;
}

/**
 * Calculate when to refresh token (1 minute before expiry)
 * More aggressive than before to prevent 401 errors
 */
function calculateRefreshTime(expiresIn: number): number {
  // Refresh 1 minute before expiry
  // E.g., for 15-minute token (900s), refresh after 14 minutes (840s)
  const refreshBeforeExpiry = 60; // seconds
  return Math.max((expiresIn - refreshBeforeExpiry) * 1000, 0);
}

/**
 * Store access token in memory and schedule refresh
 */
let accessToken: string | null = null;
let refreshTimer: NodeJS.Timeout | null = null;

/**
 * Get current access token from memory
 */
export function getAccessToken(): string | null {
  return accessToken;
}

/**
 * Store access token and schedule automatic refresh
 */
export function setTokens(tokens: TokenData): void {
  accessToken = tokens.accessToken;

  // Clear any existing refresh timer
  if (refreshTimer) {
    clearTimeout(refreshTimer);
  }

  // Schedule automatic refresh
  const refreshTime = calculateRefreshTime(tokens.expiresIn);
  console.log(
    `✅ Access token set. Auto-refresh in ${Math.floor(refreshTime / 1000)}s (expires in ${tokens.expiresIn}s)`
  );

  refreshTimer = setTimeout(async () => {
    const success = await refreshAccessToken();
    if (!success) {
      console.error("❌ Automatic token refresh failed - session may be expired");
      clearTokens();
      // Optionally redirect to login or trigger re-auth
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("auth:session-expired"));
      }
    }
  }, refreshTime);
}

/**
 * Clear tokens and cancel refresh timer
 */
export function clearTokens(): void {
  accessToken = null;

  if (refreshTimer) {
    clearTimeout(refreshTimer);
    refreshTimer = null;
  }
}

/**
 * Refresh access token using HttpOnly refresh cookie
 *
 * The refresh token is automatically sent via cookies (credentials: 'include')
 * Backend rotates the refresh token and returns new access token
 *
 * @returns true if refresh was successful, false otherwise
 */
export async function refreshAccessToken(): Promise<boolean> {
  try {
    // Call backend refresh endpoint
    // Refresh token is automatically sent via HttpOnly cookie
    const result = await serverApi.post<TokenRefreshResponse>(
      "/api/v1/auth/refresh",
      {}, // No body needed - refresh token is in cookie
      {
        credentials: "include", // Important: send cookies
      }
    );

    if (!result.ok) {
      console.error("❌ Token refresh failed:", result.message);
      return false;
    }

    // Update access token and schedule next refresh
    accessToken = result.data.accessToken;

    // Schedule next refresh
    const refreshTime = calculateRefreshTime(result.data.expiresIn);
    console.log(
      `✅ Token refreshed. Next refresh in ${Math.floor(refreshTime / 1000)}s`
    );

    if (refreshTimer) {
      clearTimeout(refreshTimer);
    }

    refreshTimer = setTimeout(async () => {
      const success = await refreshAccessToken();
      if (!success) {
        console.error("❌ Automatic token refresh failed");
        clearTokens();
        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("auth:session-expired"));
        }
      }
    }, refreshTime);

    return true;
  } catch (error) {
    console.error("❌ Error during token refresh:", error);
    return false;
  }
}

/**
 * Validate current session
 *
 * @returns User session data if valid, null otherwise
 */
export async function validateSession(): Promise<UserSession | null> {
  const token = accessToken;

  if (!token) {
    return null;
  }

  try {
    const result = await serverApi.get<{ user: UserSession }>(
      "/api/v1/auth/session",
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    if (!result.ok) {
      // If access token is expired, try to refresh
      if (result.status === 401) {
        const refreshSuccess = await refreshAccessToken();
        if (refreshSuccess) {
          // Retry validation with new token
          return await validateSession();
        }
      }
      return null;
    }

    return result.data.user;
  } catch (error) {
    console.error("❌ Error validating session:", error);
    return null;
  }
}

/**
 * Initialize tokens from login response
 *
 * Note: In stateful mode, refreshToken is NOT in the response
 * It's automatically set as HttpOnly cookie by the backend
 */
export function initializeAuth(loginResponse: {
  accessToken: string;
  expiresIn: number;
  tokenType: string;
}): void {
  setTokens({
    accessToken: loginResponse.accessToken,
    expiresIn: loginResponse.expiresIn,
    tokenType: loginResponse.tokenType,
  });
}

/**
 * Logout and clear all tokens
 *
 * Backend will revoke the session and clear the refresh cookie
 */
export async function logout(): Promise<void> {
  // Clear tokens immediately
  clearTokens();

  // Notify backend to revoke session
  // Refresh cookie is automatically sent
  try {
    await serverApi.post(
      "/api/v1/auth/logout",
      {}, // No body needed - refresh token is in cookie
      {
        credentials: "include", // Important: send cookies
      }
    );
  } catch (error) {
    console.error("❌ Error during logout:", error);
  }
}
