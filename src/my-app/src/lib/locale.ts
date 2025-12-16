/**
 * Locale Management
 *
 * Functions:
 * - getLocale() - Get current locale from cookie
 * - setLocaleCookie() - Update locale cookie
 * - changeLocale() - Persist locale to backend and reload
 */

import { apiFetch } from './api-client';
import type { Locale, LocalePreferenceResponse } from '@/src/types/locale.types';

/**
 * Get current locale from cookie
 */
export function getLocale(): Locale {
  if (typeof document === 'undefined') return 'en';
  const match = document.cookie.match(/locale=([^;]+)/);
  return (match?.[1] as Locale) || 'en';
}

/**
 * Set locale cookie
 */
export function setLocaleCookie(locale: Locale): void {
  if (typeof document === 'undefined') return;
  document.cookie = `locale=${locale}; path=/; max-age=${365 * 24 * 60 * 60}`; // 1 year
}

/**
 * Change locale - persists to backend and reloads page
 */
export async function changeLocale(locale: Locale): Promise<void> {
  // Update cookie immediately
  setLocaleCookie(locale);

  // Persist to backend
  try {
    await apiFetch<LocalePreferenceResponse>('/me/locale', {
      method: 'POST',
      body: JSON.stringify({ locale }),
    });
  } catch (error) {
    console.error('Failed to persist locale to backend:', error);
  }

  // Reload page to apply locale changes
  if (typeof window !== 'undefined') {
    window.location.reload();
  }
}
