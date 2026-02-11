"use client";

import * as React from "react";
import { FixedSizeList as List } from "react-window";
import { Check, ChevronsUpDown, Loader2, Search, User, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useDomainUsers } from "@/hooks/use-domain-users";
import { useLanguage, translate } from "@/hooks/use-language";
import type { DomainUser } from "@/types/domain-users";

// Constants
const ITEM_HEIGHT = 56; // Height for two-line items
const LIST_HEIGHT = 320; // Max height of the dropdown

const Skeleton = ({ className }: { className?: string }) => (
  <div className={cn("animate-pulse rounded-md bg-muted", className)} />
);

const DomainUserRowSkeleton = ({ style }: { style: React.CSSProperties }) => (
  <div style={style} className="flex items-center gap-3 px-3 py-2">
    <Skeleton className="h-9 w-9 rounded-full" />
    <div className="flex-1 space-y-2">
      <Skeleton className="h-4 w-48" />
      <Skeleton className="h-3 w-32" />
    </div>
  </div>
);

interface DomainUserSelectorProps {
  /** Currently selected user */
  value?: DomainUser | null;
  /** Callback when user is selected */
  onSelect: (user: DomainUser | null) => void;
  /** Placeholder text */
  placeholder?: string;
  /** Search placeholder text */
  searchPlaceholder?: string;
  /** Text shown when no results */
  emptyText?: string;
  /** Text shown on error */
  errorText?: string;
  /** Whether the selector is disabled */
  disabled?: boolean;
  /** Additional class names */
  className?: string;
}

/**
 * Row component for virtualized list
 * Renders a single domain user with two lines
 */
const DomainUserRow = React.memo(function DomainUserRow({
  index,
  style,
  data,
}: {
  index: number;
  style: React.CSSProperties;
  data: {
    items: DomainUser[];
    selectedId: number | null;
    onSelect: (user: DomainUser) => void;
    highlightedIndex: number;
    setHighlightedIndex: (index: number) => void;
  };
}) {
  const { items, selectedId, onSelect, highlightedIndex, setHighlightedIndex } =
    data;
  const user = items[index];

  if (!user) {
    return <DomainUserRowSkeleton style={style} />;
  }

  const isSelected = selectedId === user.id;
  const isHighlighted = highlightedIndex === index;

  return (
    <div
      style={style}
      role="option"
      aria-selected={isSelected}
      className={cn(
        "flex items-center gap-3 px-3 py-2 cursor-pointer transition-colors",
        isHighlighted && "bg-accent",
        isSelected && "bg-primary/10"
      )}
      onClick={() => onSelect(user)}
      onMouseEnter={() => setHighlightedIndex(index)}
    >
      {/* Avatar placeholder */}
      <div className="w-9 h-9 bg-muted flex items-center justify-center shrink-0">
        <User className="w-4 h-4 text-muted-foreground" />
      </div>

      {/* User info - two lines */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm truncate">
            {user.fullName || user.username}
          </span>
          {user.title && (
            <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded shrink-0 max-w-[150px] truncate">
              {user.title}
            </span>
          )}
        </div>
        <div className="text-xs text-muted-foreground truncate">
          {user.username}
        </div>
      </div>

      {/* Selected indicator */}
      {isSelected && (
        <Check className="w-4 h-4 text-primary shrink-0" />
      )}
    </div>
  );
});

/**
 * Performant domain user selector with virtualization and server-side search.
 *
 * Features:
 * - Server-side search with debouncing
 * - Virtualized list (react-window) for 5k+ users
 * - Two-line item display (fullName, username - office)
 * - Keyboard navigation (arrows, enter, escape)
 * - Loading and error states
 * - In-memory query caching
 */
export function DomainUserSelector({
    value,
    onSelect,
    placeholder,
    searchPlaceholder,
    emptyText,
    errorText,
    disabled = false,
    className,
  }: DomainUserSelectorProps) {
    const { t } = useLanguage();

    // Get translations with fallbacks
    const i18n = {
      selectUserPlaceholder: translate(t, 'users.selectUserPlaceholder') || "Select a user",
      searchPlaceholder: translate(t, 'users.searchPlaceholder') || "Search users...",
      noUsersFound: translate(t, 'users.add.noUsersAvailable') || "No users found",
      errorLoadingUsers: translate(t, 'users.add.errorLoadingUsers') || "Failed to load users",
      retry: translate(t, 'common.retry') || "Retry",
      showingOf: translate(t, 'users.showingOf') || "Showing {current} of {total} users",
      usersCount: translate(t, 'users.usersCount') || "{count} user(s)",
      scrollForMore: translate(t, 'users.scrollForMore') || "Scroll for more",
    };

    const [open, setOpen] = React.useState(false);
  const [highlightedIndex, setHighlightedIndex] = React.useState(0);
  const [isFetchingMore, setIsFetchingMore] = React.useState(false);
  const listRef = React.useRef<List>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const listOuterRef = React.useRef<HTMLDivElement>(null);

  // Use domain users hook with server-side search
  const {
    items,
    total,
    isLoading,
    isInitialLoading,
    error,
    hasMore,
    query,
    setQuery,
    fetchNextPage,
  } = useDomainUsers({
    limit: 50,
    debounceMs: 300,
    fetchOnMount: false, // Don't fetch until opened
  });

  // Turn off fetching state when new items arrive
  React.useEffect(() => {
    if (isFetchingMore) {
      setIsFetchingMore(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- Intentionally only reacting to items.length change
  }, [items.length]);

  // Fetch on open
  React.useEffect(() => {
    if (open) {
      // Focus input when opened
      setTimeout(() => {
        inputRef.current?.focus();
      }, 0);
    }
  }, [open]);

  // Reset highlighted index when the search query changes
  React.useEffect(() => {
    setHighlightedIndex(0);
  }, [query]);

  // Scroll highlighted item into view
  React.useEffect(() => {
    if (listRef.current && highlightedIndex >= 0) {
      listRef.current.scrollToItem(highlightedIndex, "smart");
    }
  }, [highlightedIndex]);

  // Handle user selection (defined before handleKeyDown since it's used there)
  const handleSelect = React.useCallback(
    (user: DomainUser) => {
      onSelect(user);
      setOpen(false);
      setQuery("");
    },
    [onSelect, setQuery, setOpen]
  );

  // Handle keyboard navigation
  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent) => {
      if (!open) {
        if (e.key === "Enter" || e.key === " " || e.key === "ArrowDown") {
          e.preventDefault();
          setOpen(true);
        }
        return;
      }

      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          // Only allow highlighting of loaded items
          setHighlightedIndex((prev) =>
            Math.min(prev + 1, items.length - 1)
          );
          break;
        case "ArrowUp":
          e.preventDefault();
          setHighlightedIndex((prev) => Math.max(prev - 1, 0));
          break;
        case "Enter":
          e.preventDefault();
          if (items[highlightedIndex]) {
            handleSelect(items[highlightedIndex]);
          }
          break;
        case "Escape":
          e.preventDefault();
          setOpen(false);
          break;
        case "Tab":
          setOpen(false);
          break;
      }
    },
    [open, highlightedIndex, handleSelect, items, setOpen, setHighlightedIndex]
  );

  // Handle scroll to load more
  const handleScroll = React.useCallback(
    ({
      scrollOffset,
      scrollDirection,
    }: {
      scrollOffset: number;
      scrollDirection: "forward" | "backward";
    }) => {
      if (scrollDirection !== "forward" || isFetchingMore || !hasMore) return;

      const scrollHeight = items.length * ITEM_HEIGHT;
      const scrollThreshold = scrollHeight - LIST_HEIGHT - ITEM_HEIGHT * 3;

      if (scrollOffset >= scrollThreshold) {
        setIsFetchingMore(true);
        fetchNextPage();
      }
    },
    [items.length, isFetchingMore, hasMore, fetchNextPage]
  );

  const handlePopoverWheel = (e: React.WheelEvent) => {
    const el = listOuterRef.current;
    if (el) {
      // Prevent Popover from stealing wheel events when list is scrollable
      if (el.scrollHeight > el.clientHeight) {
        e.stopPropagation();
      }
    }
  };

  // Calculate item count including skeleton loaders
  const itemCount = items.length + (isFetchingMore ? 3 : 0);

  // Get display text for trigger button
  const getDisplayText = () => {
    if (value) {
      return value.fullName || value.username;
    }
    return placeholder || i18n.selectUserPlaceholder;
  };

  // List item data (memoized to prevent unnecessary rerenders)
  const itemData = React.useMemo(
    () => ({
      items,
      selectedId: value?.id ?? null,
      onSelect: handleSelect,
      highlightedIndex,
      setHighlightedIndex,
    }),
    [items, value?.id, handleSelect, highlightedIndex]
  );

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          aria-haspopup="listbox"
          disabled={disabled}
          onKeyDown={handleKeyDown}
          className={cn(
            "w-full justify-between h-10",
            !value && "text-muted-foreground",
            className
          )}
        >
          <span className="truncate flex-1 text-start">{getDisplayText()}</span>
          <ChevronsUpDown className="ms-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>

      <PopoverContent
        className="w-[var(--radix-popover-trigger-width)] p-0"
        align="start"
        sideOffset={4}
        onWheel={handlePopoverWheel}
      >
        {/* Search input */}
        <div className="flex items-center border-b px-3 py-2">
          <Search className="h-4 w-4 text-muted-foreground me-2 shrink-0" />
          <Input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={searchPlaceholder || i18n.searchPlaceholder}
            className="h-8 border-0 p-0 focus-visible:ring-0 focus-visible:ring-offset-0"
          />
          {(isLoading || isFetchingMore) && !isInitialLoading && (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground ms-2 shrink-0" />
          )}
        </div>

        {/* Results */}
        <div role="listbox" aria-label="Domain users">
          {/* Error state */}
          {error && (
            <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
              <AlertCircle className="h-8 w-8 text-destructive mb-2" />
              <p className="text-sm text-muted-foreground">{errorText || i18n.errorLoadingUsers}</p>
              <Button
                variant="ghost"
                size="sm"
                className="mt-2"
                onClick={() => setQuery(query)} // Retry
              >
                {i18n.retry}
              </Button>
            </div>
          )}

          {/* Initial loading state */}
          {!error && isInitialLoading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          )}

          {/* Empty state */}
          {!error && !isInitialLoading && items.length === 0 && (
            <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
              <User className="h-8 w-8 text-muted-foreground mb-2" />
              <p className="text-sm text-muted-foreground">{emptyText || i18n.noUsersFound}</p>
            </div>
          )}

          {/* Virtualized list */}
          {!error && !isInitialLoading && (itemCount > 0 || items.length > 0) && (
            <>
              <List
                ref={listRef}
                outerRef={listOuterRef}
                height={Math.min(itemCount * ITEM_HEIGHT, LIST_HEIGHT)}
                itemCount={itemCount}
                itemSize={ITEM_HEIGHT}
                width="100%"
                itemData={itemData}
                onScroll={handleScroll}
                overscanCount={5}
              >
                {DomainUserRow}
              </List>

              {/* Results count */}
              <div className="px-3 py-2 border-t text-xs text-muted-foreground">
                {total > items.length
                  ? i18n.showingOf.replace("{current}", String(items.length)).replace("{total}", String(total))
                  : i18n.usersCount.replace("{count}", String(items.length))}
                {hasMore && ` · ${i18n.scrollForMore}`}
              </div>
            </>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
