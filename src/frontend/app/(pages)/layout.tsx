/**
 * Pages layout - includes navigation for authenticated pages.
 *
 * This layout wraps all authenticated pages (everything except auth routes).
 * Navigation is only rendered here, not in the root layout.
 */

import { AppNavigationServer } from "@/components/navigation/app-navigation-server";

export default function PagesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col h-full min-h-0">
      <AppNavigationServer />
      <main className="flex-1 min-h-0 overflow-auto">
        {children}
      </main>
    </div>
  );
}
