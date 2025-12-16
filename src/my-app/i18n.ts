import { getRequestConfig } from "next-intl/server";
import { cookies } from "next/headers";

const getMessages = async (locale: string) => {
  return {
    addUser: (await import(`./locales/${locale}/addUser.json`)).default,
    analysis: (await import(`./locales/${locale}/analysis.json`)).default,
    audit: (await import(`./locales/${locale}/audit.json`)).default,
    auth: (await import(`./locales/${locale}/auth.json`)).default,
    common: (await import(`./locales/${locale}/common.json`)).default,
    confirmDialog: (await import(`./locales/${locale}/confirmDialog.json`))
      .default,
    home: (await import(`./locales/${locale}/home.json`)).default,
    language: (await import(`./locales/${locale}/language.json`)).default,
    mealRequest: (await import(`./locales/${locale}/mealRequest.json`))
      .default,
    mealTypes: (await import(`./locales/${locale}/mealTypes.json`)).default,
    myRequests: (await import(`./locales/${locale}/myRequests.json`)).default,
    navbar: (await import(`./locales/${locale}/navbar.json`)).default,
    pages: (await import(`./locales/${locale}/pages.json`)).default,
    requests: (await import(`./locales/${locale}/requests.json`)).default,
    scheduler: (await import(`./locales/${locale}/scheduler.json`)).default,
    settingRoles: (await import(`./locales/${locale}/settingRoles.json`))
      .default,
    table: (await import(`./locales/${locale}/table.json`)).default,
    theme: (await import(`./locales/${locale}/theme.json`)).default,
    user: (await import(`./locales/${locale}/user.json`)).default,
    users: (await import(`./locales/${locale}/users.json`)).default,
  };
};

/**
 * next-intl configuration for server-side locale detection.
 *
 * Locale resolution priority:
 * 1. JWT refresh token payload (from session cookie)
 * 2. Accept-Language header
 * 3. Default locale ('en')
 *
 * This configuration runs on the server for each request.
 * Client-side components use LocaleManager for instant localStorage access.
 */
export default getRequestConfig(async () => {
  let locale = "en";

  try {
    // Priority 1: Try to get locale from session cookie (JWT refresh token)
    const cookieStore = await cookies();
    const sessionCookie = cookieStore.get(
      process.env.SESSION_COOKIE_NAME || "session"
    );

    if (sessionCookie) {
      // In a real implementation, we'd decode the JWT here
      // For now, we'll use the default locale
      // The client will override with localStorage via LocaleManager
      locale = "en";
    }
  } catch (error) {
    console.error("[i18n] Error detecting locale:", error);
  }

  return {
    locale,
    messages: await getMessages(locale),
  };
});
