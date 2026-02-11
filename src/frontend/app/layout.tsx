/**
 * Root layout component (server component).
 *
 * This layout provides the base HTML structure and global providers.
 * Navigation is handled by route group layouts:
 * - (pages) layout includes navigation for authenticated pages
 * - (auth) layout has no navigation for login/auth pages
 */

import type { Metadata } from "next";
import { cookies } from "next/headers";
import { NextIntlClientProvider } from 'next-intl';
import { getMessages } from 'next-intl/server';
import { Cairo } from 'next/font/google';
import ClientAppWrapper from "@/components/client-app-wrapper/client-app-wrapper";
import { checkToken } from "@/lib/auth/check-token";
import "./globals.css";

// Configure Cairo font for Arabic
const cairo = Cairo({
  subsets: ['arabic', 'latin'],
  weight: ['400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-cairo',
});

export const metadata: Metadata = {
  title: "Meal Request System",
  description: "Secure meal request management application",
};

/**
 * Root layout - server component.
 *
 * Provides global context (session, theme, translations) to all pages.
 * Navigation is NOT included here - it's in (pages)/layout.tsx instead.
 */
export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // Fetch session on the server (may be null for unauthenticated users)
  const sessionResult = await checkToken();
  const session = sessionResult.ok && sessionResult.user ? sessionResult.user : null;

  // Get language preference with correct priority:
  // 1. Locale cookie (user's explicit choice / server-set)
  // 2. User's session locale (from JWT via checkToken)
  // 3. Default to 'en'
  const cookieStore = await cookies();
  const localeCookie = cookieStore.get('locale')?.value;
  const resolvedLocale = localeCookie || session?.locale || 'en';
  const initialLanguage = resolvedLocale.toLowerCase() === 'ar' ? 'ar' : 'en';

  // Get initial direction based on language
  const dir = initialLanguage === 'ar' ? 'rtl' : 'ltr';

  // Load translations for next-intl
  const messages = await getMessages();

  return (
    <html lang={initialLanguage} dir={dir} suppressHydrationWarning className={cairo.variable}>
      <head>
        {/* Preload critical logo image to avoid layout shift */}
        <link rel="preload" href="/logo.png" as="image" />
      </head>
      <body className={`antialiased ${initialLanguage === 'ar' ? 'font-cairo' : ''}`}>
        <NextIntlClientProvider locale={initialLanguage} messages={messages}>
          <ClientAppWrapper initialSession={session} initialLanguage={initialLanguage}>
            {children}
          </ClientAppWrapper>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
