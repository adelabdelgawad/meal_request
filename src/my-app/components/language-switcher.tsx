'use client';

import * as React from 'react';
import { ChevronDown, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useLanguage } from '@/hooks/use-language';

const languages = [
  { code: 'en' as const, label: 'English', nativeLabel: 'English', flag: '🇺🇸' },
  { code: 'ar' as const, label: 'Arabic', nativeLabel: 'العربية', flag: '🇸🇦' },
];

export function LanguageSwitcher() {
  const { language, setLanguage } = useLanguage();
  const [isUpdating, setIsUpdating] = React.useState(false);

  const handleLanguageChange = async (newLocale: 'en' | 'ar') => {
    if (newLocale === language || isUpdating) return;

    setIsUpdating(true);
    try {

      // 1. Update context state immediately (triggers re-render of all consuming components)
      //    This also updates the locale cookie via LocaleManager.setLocale()
      setLanguage(newLocale);

      // 2. Call backend to persist to database and update JWT (async, non-blocking)
      //    Backend will set the authoritative locale cookie in its response
      fetch('/api/auth/locale', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ locale: newLocale }),
      }).catch(error => {
        console.error('[LanguageSwitcher] Backend update failed:', error);
        // Don't revert - user still sees correct language from cookie/context
      });

    } catch (error) {
      console.error('[LanguageSwitcher] Error:', error);
    } finally {
      setIsUpdating(false);
    }
  };

  // Get current language object for display
  const currentLanguage = languages.find(lang => lang.code === language) || languages[0];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className="h-9 gap-2 px-3 hover:bg-accent/10"
          disabled={isUpdating}
          suppressHydrationWarning
        >
          {isUpdating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <>
              <span className="text-lg leading-none" suppressHydrationWarning>{currentLanguage.flag}</span>
              <span className="text-sm font-medium" suppressHydrationWarning>{currentLanguage.label}</span>
              <ChevronDown className="h-4 w-4 opacity-50" />
            </>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-[160px]">
        {languages.map((lang) => (
          <DropdownMenuItem
            key={lang.code}
            onClick={() => handleLanguageChange(lang.code)}
            className={`cursor-pointer ${language === lang.code ? 'bg-accent' : ''}`}
            disabled={isUpdating}
          >
            <span className="me-3 text-lg">{lang.flag}</span>
            <span className="text-sm font-medium">{lang.label}</span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
