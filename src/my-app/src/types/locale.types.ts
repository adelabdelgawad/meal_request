/**
 * Locale Types
 */

export type Locale = 'en' | 'ar';

export interface LocalePreferenceRequest {
  locale: Locale;
}

export interface LocalePreferenceResponse {
  message: string;
  locale: Locale;
}
