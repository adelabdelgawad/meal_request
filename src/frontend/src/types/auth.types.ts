/**
 * Authentication Types
 * All types use camelCase to match backend CamelModel responses
 */

export interface LoginRequest {
  username: string;
  password: string;
  scope?: 'local' | 'domain';
}

export interface LoginResponse {
  accessToken: string;
  tokenType: 'bearer';
  expiresIn: number;
  user: UserInfo;
  pages: LocalizedPage[];
  refreshToken?: string; // Only present if USE_STATEFUL_SESSIONS=false
}

export interface UserInfo {
  id: string;
  username: string;
  isSuperAdmin: boolean;
  locale?: string;
}

export interface LocalizedPage {
  id: number;
  name: string;
  description: string;
  nameEn: string;
  nameAr: string;
  descriptionEn: string | null;
  descriptionAr: string | null;
}

export interface TokenResponse {
  accessToken: string;
  tokenType: 'bearer';
  expiresIn: number;
}

export interface SessionResponse {
  ok: boolean;
  user: {
    id: string;
    username: string;
    roles: string[];
    scopes: string[];
    pages: Array<{ id: number; name: string }>;
  };
}
