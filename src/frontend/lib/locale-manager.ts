'use client';

const LOCALE_COOKIE_NAME = 'locale';
const LOCALE_LOCALSTORAGE_KEY = 'locale'; // For migration only
const SUPPORTED_LOCALES = ['en', 'ar'] as const;
type SupportedLocale = typeof SUPPORTED_LOCALES[number];

// Cookie max age: 1 year in seconds
const LOCALE_COOKIE_MAX_AGE = 365 * 24 * 60 * 60;

/**
 * LocaleManager - Client-side locale persistence with cookies.
 *
 * Uses cookies as the single source of truth for locale (SSR-friendly).
 * Syncs with backend via /api/auth/locale endpoint when locale changes.
 *
 * Migration: On first access, migrates any existing localStorage locale to cookie.
 */
export class LocaleManager {
  private static migrationDone = false;

  /**
   * Get current locale from cookie.
   *
   * Fallback order:
   * 1. Cookie (user's explicit choice / server-set)
   * 2. Browser language (if supported)
   * 3. Default locale ('en')
   *
   * Also performs one-time migration from localStorage to cookie.
   *
   * @returns Current locale code ('en' or 'ar')
   */
  static getLocale(): SupportedLocale {
    if (typeof window === 'undefined') {
      return 'en'; // Server-side default
    }

    // Perform one-time migration from localStorage to cookie
    this.migrateFromLocalStorage();

    // Priority 1: Cookie (user's explicit choice / server-set)
    const cookieLocale = this.getCookie(LOCALE_COOKIE_NAME);
    if (cookieLocale && this.isValidLocale(cookieLocale)) {
      return cookieLocale as SupportedLocale;
    }

    // Priority 2: Browser language
    const browserLang = navigator.language.split('-')[0];
    if (this.isValidLocale(browserLang)) {
      const locale = browserLang as SupportedLocale;
      this.setLocaleCookie(locale); // Cache it in cookie
      return locale;
    }

    // Priority 3: Default
    return 'en';
  }

  /**
   * Set locale in cookie.
   *
   * Updates cookie immediately (synchronous, no network request).
   * Call /api/auth/locale separately to sync with backend and database.
   *
   * @param locale - Locale code ('en' or 'ar')
   */
  static setLocale(locale: SupportedLocale): void {
    if (typeof window === 'undefined') return;

    if (!this.isValidLocale(locale)) {
      console.error(`[LocaleManager] Invalid locale: ${locale}`);
      return;
    }

    this.setLocaleCookie(locale);
  }

  /**
   * Migrate locale from localStorage to cookie (one-time operation).
   *
   * If there's a localStorage locale but no cookie, migrate it and remove localStorage.
   * This ensures backward compatibility with existing users.
   */
  private static migrateFromLocalStorage(): void {
    if (this.migrationDone || typeof window === 'undefined') return;
    this.migrationDone = true;

    try {
      const cookieLocale = this.getCookie(LOCALE_COOKIE_NAME);
      const localStorageLocale = localStorage.getItem(LOCALE_LOCALSTORAGE_KEY);

      // Only migrate if there's no cookie but there is localStorage
      if (!cookieLocale && localStorageLocale && this.isValidLocale(localStorageLocale)) {
        this.setLocaleCookie(localStorageLocale as SupportedLocale);

        // Remove localStorage after successful migration
        localStorage.removeItem(LOCALE_LOCALSTORAGE_KEY);

        // Notify backend about the migrated locale (fire and forget)
        this.syncMigratedLocaleToBackend(localStorageLocale as SupportedLocale);
      }
    } catch (error) {
      console.error('[LocaleManager] Migration error:', error);
    }
  }

  /**
   * Sync migrated locale to backend (async, non-blocking).
   */
  private static syncMigratedLocaleToBackend(locale: SupportedLocale): void {
    fetch('/api/auth/locale', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ locale }),
    }).catch(error => {
      console.warn('[LocaleManager] Failed to sync migrated locale to backend:', error);
    });
  }

  /**
   * Get cookie value by name.
   */
  private static getCookie(name: string): string | null {
    if (typeof document === 'undefined') return null;

    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const [cookieName, cookieValue] = cookie.trim().split('=');
      if (cookieName === name) {
        return decodeURIComponent(cookieValue);
      }
    }
    return null;
  }

  /**
   * Set locale cookie with proper attributes.
   */
  private static setLocaleCookie(locale: SupportedLocale): void {
    if (typeof document === 'undefined') return;

    // Build cookie string with proper attributes
    const cookieValue = [
      `${LOCALE_COOKIE_NAME}=${encodeURIComponent(locale)}`,
      `path=/`,
      `max-age=${LOCALE_COOKIE_MAX_AGE}`,
      `samesite=lax`,
    ];

    // Only add Secure flag in production (HTTPS)
    if (window.location.protocol === 'https:') {
      cookieValue.push('secure');
    }

    document.cookie = cookieValue.join('; ');
  }

  /**
   * Validate locale code.
   *
   * @param locale - Locale code to validate
   * @returns True if locale is supported
   */
  private static isValidLocale(locale: string): boolean {
    return SUPPORTED_LOCALES.includes(locale as SupportedLocale);
  }

  /**
   * Get supported locales list.
   *
   * @returns Array of supported locale codes
   */
  static getSupportedLocales(): readonly SupportedLocale[] {
    return SUPPORTED_LOCALES;
  }

  /**
   * Clear locale cookie.
   *
   * Resets to default locale on next getLocale() call.
   */
  static clearLocale(): void {
    if (typeof document === 'undefined') return;

    // Clear cookie by setting max-age to 0
    document.cookie = `${LOCALE_COOKIE_NAME}=; path=/; max-age=0`;
  }

  /**
   * Check if locale cookie exists.
   *
   * @returns True if locale cookie is set
   */
  static hasLocaleCookie(): boolean {
    return this.getCookie(LOCALE_COOKIE_NAME) !== null;
  }
}
