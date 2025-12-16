/**
 * Client-side auth actions
 * DEPRECATED: Use src/lib/auth.ts instead
 * This file is kept for backward compatibility during migration
 */

// Import types from centralized location
export type { LoginRequest, LoginResponse } from '@/src/types/auth.types';
import { login } from '@/src/lib/auth';

interface LoginCredentials {
  username: string;
  password: string;
}

/**
 * Log in a user
 * @deprecated Use `login()` from '@/lib/auth' instead
 */
export async function loginAction(credentials: LoginCredentials) {
  return login(credentials);
}
