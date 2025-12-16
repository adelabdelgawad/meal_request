'use client';

import { useLanguage } from '@/hooks/use-language';

interface LiveIndicatorProps {
  isLive: boolean;
  isValidating?: boolean;
  filtersActive?: boolean;
}

export function LiveIndicator({ isLive, isValidating, filtersActive = false }: LiveIndicatorProps) {
  const { t } = useLanguage();

  // Get translations
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const live = ((t?.requests as Record<string, unknown>)?.live || {}) as any;

  // When filters are active, force offline mode
  const displayAsOffline = filtersActive || !isLive;
  const displayText = isValidating
    ? (live.updating || 'Updating...')
    : (displayAsOffline ? (live.inactive || 'Offline') : (live.live || 'Live'));

  return (
    <div className="flex items-center gap-2">
      <span className={`text-sm font-medium ${displayAsOffline ? 'text-muted-foreground' : 'text-green-600 dark:text-green-400'}`}>
        {displayText}
      </span>
      <div
        className={`w-2.5 h-2.5 rounded-full ${
          displayAsOffline ? 'bg-muted-foreground' : 'bg-green-500 dark:bg-green-400'
        } ${isValidating ? 'animate-pulse' : ''}`}
      />
    </div>
  );
}
