"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, LogOut, ChevronDown, WifiOff } from "lucide-react";

import {
  NavigationMenu,
  NavigationMenuContent,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  NavigationMenuTrigger,
  navigationMenuTriggerStyle,
} from "@/components/ui/navigation-menu";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { useSession } from "@/lib/auth/use-session";
import { useLanguage, translate } from "@/hooks/use-language";
import { cn } from "@/lib/utils";
import type { User, Page } from "@/lib/auth/check-token";

// New components
import { UserAvatar } from "@/components/user-avatar";
import { ModeToggle } from "@/components/mode-toggle";
import { LanguageSwitcher } from "@/components/language-switcher";

interface AppNavigationClientProps {
  initialUser: User;
  /** True if backend was unreachable during server render */
  initialOffline?: boolean;
}

/**
 * Helper to organize pages into a hierarchical structure.
 * Returns parent pages with their children attached.
 */
function organizePages(pages: Page[]): {
  topLevelPages: Page[];
  childrenByParentId: Map<number, Page[]>;
} {
  const topLevelPages: Page[] = [];
  const childrenByParentId = new Map<number, Page[]>();

  // First pass: identify parent pages and group children
  for (const page of pages) {
    if (page.parentId == null) {
      topLevelPages.push(page);
    } else {
      const children = childrenByParentId.get(page.parentId) || [];
      children.push(page);
      childrenByParentId.set(page.parentId, children);
    }
  }

  return { topLevelPages, childrenByParentId };
}

/**
 * Helper to convert page name to URL slug.
 */
function getPageSlug(page: Page): string {
  return `/${page.nameEn.toLowerCase().replace(/\s+/g, "-")}`;
}

/**
 * Client-side navigation menu component.
 *
 * Receives server-validated user data as prop to avoid flash.
 * Also subscribes to session context for live updates.
 *
 * Features:
 * - Automatically displays user's accessible pages
 * - Hierarchical menu support (parent pages with dropdowns)
 * - Updates when token is refreshed (session hook integration)
 * - Responsive design with mobile sheet menu
 * - Active page highlighting
 * - User menu with logout
 * - Theme toggle
 * - Language switcher
 */
export function AppNavigationClient({ initialUser, initialOffline = false }: AppNavigationClientProps) {
  const { user, refresh, isRefreshing } = useSession();
  const { language, t } = useLanguage();
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const [expandedMenus, setExpandedMenus] = React.useState<Set<number>>(new Set());
  const [isOffline, setIsOffline] = React.useState(initialOffline);

  // Use session user if available (for live updates), otherwise use initial user
  const currentUser = user || initialUser;

  // When session loads successfully, we're back online
  React.useEffect(() => {
    if (user && !isRefreshing) {
      setIsOffline(false);
    }
  }, [user, isRefreshing]);

  // Attempt to reconnect when initially offline
  React.useEffect(() => {
    if (initialOffline) {
      // Try to refresh session after a short delay
      const timer = setTimeout(() => {
        refresh().catch(() => {
          // Still offline, keep the state
          setIsOffline(true);
        });
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [initialOffline, refresh]);

  const pages = React.useMemo(() => currentUser?.pages || [], [currentUser?.pages]);
  // Use language context as primary (user selection), fallback to user's saved locale
  const locale = language || currentUser?.locale || "en";

  // Organize pages hierarchically
  const { topLevelPages, childrenByParentId } = organizePages(pages);

  // Debug logging for avatar and language
  React.useEffect(() => {
    if (pages.length === 0) {
      console.error("[AppNavigation] ⚠️ NO PAGES FOUND! User has empty pages array");
    }

  }, [language, locale, currentUser, pages]);

  // Don't show navigation on auth pages
  if (pathname?.startsWith("/login") || pathname?.startsWith("/auth")) {
    return null;
  }

  // Toggle mobile submenu expansion
  const toggleMobileMenu = (pageId: number) => {
    setExpandedMenus((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(pageId)) {
        newSet.delete(pageId);
      } else {
        newSet.add(pageId);
      }
      return newSet;
    });
  };

  const handleLogout = async () => {
    try {

      const response = await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "include",
      });

      const data = await response.json();

      if (response.ok) {
        await refresh();
        setTimeout(() => {
          window.location.href = "/login";
        }, 100);
      } else {
        console.error("[AppNavigation] Logout failed:", data);
        window.location.href = "/login";
      }
    } catch (error) {
      console.error("[AppNavigation] Logout error:", error);
      try {
        await refresh();
      } catch (refreshError) {
        console.error("[AppNavigation] Could not refresh session context:", refreshError);
      }
      window.location.href = "/login";
    }
  };

  return (
    <>
      {/* Desktop Navigation */}
      <div className="hidden md:flex md:flex-1" dir={language === 'ar' ? 'rtl' : 'ltr'}>
        <NavigationMenu key={language} dir={language === 'ar' ? 'rtl' : 'ltr'}>
          <NavigationMenuList>
            {/* Home */}
            <NavigationMenuItem>
              <NavigationMenuLink asChild>
                <Link
                  href="/"
                  className={cn(
                    navigationMenuTriggerStyle(),
                    pathname === "/" && "bg-accent"
                  )}
                  suppressHydrationWarning
                >
                  {translate(t, 'navbar.home')}
                </Link>
              </NavigationMenuLink>
            </NavigationMenuItem>

            {/* Dynamic Pages from User Permissions - Hierarchical */}
            {topLevelPages.map((page) => {
              const pageName = locale === "ar" ? page.nameAr : page.nameEn;
              const pageDescription = locale === "ar" ? page.descriptionAr : page.descriptionEn;
              const pageSlug = getPageSlug(page);
              const children = childrenByParentId.get(page.id) || [];

              // If this page has children, render as dropdown
              if (children.length > 0) {
                return (
                  <NavigationMenuItem key={page.id}>
                    <NavigationMenuTrigger
                      className={cn(
                        pathname?.startsWith(pageSlug) && "bg-accent"
                      )}
                      suppressHydrationWarning
                    >
                      {pageName}
                    </NavigationMenuTrigger>
                    <NavigationMenuContent>
                      <ul className="grid w-[400px] gap-1 p-2">
                        {children.map((child) => {
                          const childName = locale === "ar" ? child.nameAr : child.nameEn;
                          const childDescription = locale === "ar" ? child.descriptionAr : child.descriptionEn;
                          const childSlug = getPageSlug(child);

                          return (
                            <li key={child.id}>
                              <NavigationMenuLink asChild>
                                <Link
                                  href={childSlug}
                                  className={cn(
                                    "block select-none space-y-1 rounded-md p-3 leading-none no-underline outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground",
                                    pathname === childSlug && "bg-accent"
                                  )}
                                  title={childDescription || undefined}
                                  suppressHydrationWarning
                                >
                                  <div className="text-sm font-medium leading-none" suppressHydrationWarning>
                                    {childName}
                                  </div>
                                  {childDescription && (
                                    <p className="line-clamp-2 text-sm leading-snug text-muted-foreground" suppressHydrationWarning>
                                      {childDescription}
                                    </p>
                                  )}
                                </Link>
                              </NavigationMenuLink>
                            </li>
                          );
                        })}
                      </ul>
                    </NavigationMenuContent>
                  </NavigationMenuItem>
                );
              }

              // No children - render as regular link
              return (
                <NavigationMenuItem key={page.id}>
                  <NavigationMenuLink asChild>
                    <Link
                      href={pageSlug}
                      className={cn(
                        navigationMenuTriggerStyle(),
                        pathname === pageSlug && "bg-accent"
                      )}
                      title={pageDescription || undefined}
                      suppressHydrationWarning
                    >
                      {pageName}
                    </Link>
                  </NavigationMenuLink>
                </NavigationMenuItem>
              );
            })}
          </NavigationMenuList>
          </NavigationMenu>
        </div>

        {/* Desktop Right Side Controls */}
        <div className="hidden md:flex md:items-center md:gap-2">
          {/* Offline Indicator */}
          {isOffline && (
            <div className="flex items-center gap-1.5 px-2 py-1 text-xs font-medium text-yellow-600 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/30 rounded-md">
              <WifiOff className="h-3.5 w-3.5" />
              <span suppressHydrationWarning>{translate(t, 'navbar.offline') || 'Offline'}</span>
            </div>
          )}

          {/* Language Switcher */}
          <LanguageSwitcher />

          {/* Theme Toggle */}
          <ModeToggle />

          {/* User Avatar */}
          {currentUser && (
            <UserAvatar user={currentUser} onLogout={handleLogout} />
          )}
        </div>

        {/* Mobile Menu */}
        <div className="flex flex-1 items-center justify-end gap-2 md:hidden">
          {/* Theme Toggle (Mobile) */}
          <ModeToggle />

          <Sheet key={language} open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="md:hidden h-11 w-11">
                <Menu className="h-5 w-5" />
                <span className="sr-only">Toggle menu</span>
              </Button>
            </SheetTrigger>
            <SheetContent side={language === 'ar' ? 'left' : 'right'} className="w-[300px] sm:w-[400px]">
              <div className="flex flex-col space-y-4 mt-4">
                {/* User Info */}
                {currentUser && (
                  <div className="flex items-start space-x-3 border-b pb-4">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary">
                      <span className="text-sm font-bold text-primary-foreground" suppressHydrationWarning>
                        {currentUser?.fullName?.[0] || currentUser?.username?.[0] || 'U'}
                      </span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium truncate" suppressHydrationWarning>
                        {currentUser?.username || "User"}
                      </p>
                      {currentUser?.fullName && (
                        <p className="text-sm text-muted-foreground truncate" suppressHydrationWarning>
                          {currentUser.fullName}
                        </p>
                      )}
                      {currentUser?.title && (
                        <p className="text-xs text-muted-foreground truncate" suppressHydrationWarning>
                          {currentUser.title}
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* Offline Indicator (Mobile) */}
                {isOffline && (
                  <div className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-yellow-600 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/30 rounded-md mx-3">
                    <WifiOff className="h-4 w-4" />
                    <span suppressHydrationWarning>{translate(t, 'navbar.offline') || 'Offline'}</span>
                  </div>
                )}

                {/* Language Switcher (Mobile) */}
                <div className="flex items-center justify-between px-3 py-2 border-b">
                  <span className="text-sm font-medium" suppressHydrationWarning>{translate(t, 'user.locale')}</span>
                  <LanguageSwitcher />
                </div>

                {/* Navigation Links */}
                <nav className="flex flex-col space-y-2">
                  <Link
                    href="/"
                    className={cn(
                      "rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
                      pathname === "/" && "bg-accent"
                    )}
                    onClick={() => setMobileMenuOpen(false)}
                    suppressHydrationWarning
                  >
                    {translate(t, 'navbar.home')}
                  </Link>

                  {/* Hierarchical Mobile Navigation */}
                  {topLevelPages.map((page) => {
                    const pageName = locale === "ar" ? page.nameAr : page.nameEn;
                    const pageSlug = getPageSlug(page);
                    const children = childrenByParentId.get(page.id) || [];

                    // If this page has children, render as collapsible
                    if (children.length > 0) {
                      return (
                        <Collapsible
                          key={page.id}
                          open={expandedMenus.has(page.id)}
                          onOpenChange={() => toggleMobileMenu(page.id)}
                        >
                          <CollapsibleTrigger asChild>
                            <button
                              className={cn(
                                "flex w-full items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
                                pathname?.startsWith(pageSlug) && "bg-accent"
                              )}
                              suppressHydrationWarning
                            >
                              {pageName}
                              <ChevronDown
                                className={cn(
                                  "h-4 w-4 transition-transform",
                                  expandedMenus.has(page.id) && "rotate-180"
                                )}
                              />
                            </button>
                          </CollapsibleTrigger>
                          <CollapsibleContent className="ps-4 pt-1">
                            {children.map((child) => {
                              const childName = locale === "ar" ? child.nameAr : child.nameEn;
                              const childSlug = getPageSlug(child);

                              return (
                                <Link
                                  key={child.id}
                                  href={childSlug}
                                  className={cn(
                                    "block rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
                                    pathname === childSlug && "bg-accent"
                                  )}
                                  onClick={() => setMobileMenuOpen(false)}
                                  suppressHydrationWarning
                                >
                                  {childName}
                                </Link>
                              );
                            })}
                          </CollapsibleContent>
                        </Collapsible>
                      );
                    }

                    // No children - render as regular link
                    return (
                      <Link
                        key={page.id}
                        href={pageSlug}
                        className={cn(
                          "rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
                          pathname === pageSlug && "bg-accent"
                        )}
                        onClick={() => setMobileMenuOpen(false)}
                        suppressHydrationWarning
                      >
                        {pageName}
                      </Link>
                    );
                  })}

                  <button
                    onClick={() => {
                      setMobileMenuOpen(false);
                      handleLogout();
                    }}
                    className="flex items-center rounded-md px-3 py-2 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10"
                    suppressHydrationWarning
                  >
                    <LogOut className="me-2 h-4 w-4" />
                    {translate(t, 'navbar.logout')}
                  </button>
                </nav>
              </div>
            </SheetContent>
          </Sheet>
        </div>
    </>
  );
}

/**
 * List item component for navigation menu content.
 */
const ListItem = React.forwardRef<
  React.ElementRef<"a">,
  React.ComponentPropsWithoutRef<"a"> & { title: string }
>(({ className, title, children, href, ...props }, ref) => {
  return (
    <li>
      <NavigationMenuLink asChild>
        <Link
          ref={ref}
          href={href || "#"}
          className={cn(
            "block select-none space-y-1 rounded-md p-3 leading-none no-underline outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground",
            className
          )}
          {...props}
        >
          <div className="text-sm font-medium leading-none">{title}</div>
          <p className="line-clamp-2 text-sm leading-snug text-muted-foreground">
            {children}
          </p>
        </Link>
      </NavigationMenuLink>
    </li>
  );
});
ListItem.displayName = "ListItem";
