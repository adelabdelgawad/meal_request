/**
 * Datetime utilities for consistent timezone handling in the frontend.
 *
 * CRITICAL: The backend always sends datetimes in UTC with 'Z' suffix (ISO 8601).
 * These utilities ensure proper parsing and display in the user's local timezone.
 *
 * Example backend response:
 * {
 *   "createdAt": "2025-12-12T15:00:00Z"  // UTC time
 * }
 *
 * Frontend should display:
 * - "Dec 12, 5:00 PM" (if user is in EET, UTC+2)
 * - "Dec 12, 3:00 PM" (if user is in UTC)
 * - "2 hours ago" (relative time)
 */

import { format, formatDistanceToNow, parseISO, isValid } from 'date-fns';
import { ar, enUS } from 'date-fns/locale';

/**
 * Get the appropriate date-fns locale based on current language.
 *
 * @param language - Current UI language ('en' or 'ar')
 * @returns date-fns locale object
 */
export function getDateLocale(language: string) {
  return language === 'ar' ? ar : enUS;
}

/**
 * Parse a UTC datetime string from the API into a Date object.
 *
 * The API always returns datetimes in UTC with 'Z' suffix: "2025-12-12T15:00:00Z"
 * This function parses it and returns a Date object that represents
 * that moment in time (which the browser will display in the user's local timezone).
 *
 * @param dateString - ISO 8601 datetime string with 'Z' suffix
 * @returns Date object or null if invalid
 *
 * @example
 * // API returns: "2025-12-12T15:00:00Z"
 * const date = parseUTCDate("2025-12-12T15:00:00Z");
 * // Date object representing UTC 15:00, displayed as local time by browser
 */
export function parseUTCDate(dateString: string | null | undefined): Date | null {
  if (!dateString) {
    return null;
  }

  try {
    const date = parseISO(dateString);
    return isValid(date) ? date : null;
  } catch {
    return null;
  }
}

/**
 * Format a datetime for display in the user's local timezone.
 *
 * @param dateString - ISO 8601 datetime string from API
 * @param formatString - date-fns format string (default: 'dd/MM/yyyy HH:mm:ss')
 * @param language - Current UI language for locale-specific formatting
 * @returns Formatted datetime string in user's local timezone or empty string if invalid
 *
 * @example
 * // API: "2025-12-12T15:00:00Z" (UTC)
 * // User in EET (UTC+2):
 * formatDateTime("2025-12-12T15:00:00Z")  // "12/12/2025 17:00:00"
 * formatDateTime("2025-12-12T15:00:00Z", "dd MMM yyyy, HH:mm")  // "12 Dec 2025, 17:00"
 */
export function formatDateTime(
  dateString: string | null | undefined,
  formatString: string = 'dd/MM/yyyy HH:mm:ss',
  language: string = 'en'
): string {
  const date = parseUTCDate(dateString);
  if (!date) {
    return '';
  }

  const locale = getDateLocale(language);
  return format(date, formatString, { locale });
}

/**
 * Format a datetime as a relative time string ("2 hours ago", "in 5 minutes").
 *
 * @param dateString - ISO 8601 datetime string from API
 * @param language - Current UI language for locale-specific formatting
 * @param addSuffix - Whether to add "ago" or "in" suffix (default: true)
 * @returns Relative time string or empty string if invalid
 *
 * @example
 * // API: "2025-12-12T13:00:00Z", current time: "2025-12-12T15:00:00Z"
 * formatRelativeTime("2025-12-12T13:00:00Z")  // "2 hours ago"
 * formatRelativeTime("2025-12-12T13:00:00Z", "ar")  // "منذ ساعتين" (in Arabic)
 */
export function formatRelativeTime(
  dateString: string | null | undefined,
  language: string = 'en',
  addSuffix: boolean = true
): string {
  const date = parseUTCDate(dateString);
  if (!date) {
    return '';
  }

  const locale = getDateLocale(language);
  return formatDistanceToNow(date, { addSuffix, locale });
}

/**
 * Format a datetime with both absolute and relative time.
 *
 * @param dateString - ISO 8601 datetime string from API
 * @param language - Current UI language
 * @returns Combined format: "Dec 12, 5:00 PM (2 hours ago)" or empty string if invalid
 *
 * @example
 * formatDateTimeWithRelative("2025-12-12T15:00:00Z")  // "12/12/2025 17:00 (2 hours ago)"
 */
export function formatDateTimeWithRelative(
  dateString: string | null | undefined,
  language: string = 'en'
): string {
  const date = parseUTCDate(dateString);
  if (!date) {
    return '';
  }

  const absolute = formatDateTime(dateString, 'dd/MM/yyyy HH:mm', language);
  const relative = formatRelativeTime(dateString, language);

  return `${absolute} (${relative})`;
}

/**
 * Format only the date portion (no time).
 *
 * @param dateString - ISO 8601 datetime string from API
 * @param formatString - date-fns format string (default: 'dd/MM/yyyy')
 * @param language - Current UI language
 * @returns Formatted date string or empty string if invalid
 *
 * @example
 * formatDate("2025-12-12T15:00:00Z")  // "12/12/2025"
 * formatDate("2025-12-12T15:00:00Z", "MMM dd, yyyy")  // "Dec 12, 2025"
 */
export function formatDate(
  dateString: string | null | undefined,
  formatString: string = 'dd/MM/yyyy',
  language: string = 'en'
): string {
  const date = parseUTCDate(dateString);
  if (!date) {
    return '';
  }

  const locale = getDateLocale(language);
  return format(date, formatString, { locale });
}

/**
 * Format only the time portion (no date).
 *
 * @param dateString - ISO 8601 datetime string from API
 * @param formatString - date-fns format string (default: 'HH:mm:ss')
 * @param language - Current UI language
 * @returns Formatted time string in user's local timezone or empty string if invalid
 *
 * @example
 * // API: "2025-12-12T15:00:00Z" (UTC)
 * // User in EET (UTC+2):
 * formatTime("2025-12-12T15:00:00Z")  // "17:00:00"
 * formatTime("2025-12-12T15:00:00Z", "h:mm a")  // "5:00 PM"
 */
export function formatTime(
  dateString: string | null | undefined,
  formatString: string = 'HH:mm:ss',
  language: string = 'en'
): string {
  const date = parseUTCDate(dateString);
  if (!date) {
    return '';
  }

  const locale = getDateLocale(language);
  return format(date, formatString, { locale });
}

/**
 * Check if a datetime string is valid.
 *
 * @param dateString - String to validate
 * @returns true if valid ISO 8601 datetime, false otherwise
 */
export function isValidDateTime(dateString: string | null | undefined): boolean {
  const date = parseUTCDate(dateString);
  return date !== null;
}

/**
 * Get the user's local timezone name.
 *
 * @returns Timezone name like "Africa/Cairo", "Europe/London", etc.
 */
export function getUserTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

/**
 * Get the user's timezone offset in hours.
 *
 * @returns Offset in hours (e.g., 2 for UTC+2, -5 for UTC-5)
 */
export function getUserTimezoneOffset(): number {
  const offset = new Date().getTimezoneOffset(); // Minutes, reversed sign
  return -offset / 60; // Convert to hours with correct sign
}
