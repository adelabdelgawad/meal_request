import { useState, useEffect, useCallback, useRef } from "react";
import { fetchDomainUsers } from "@/lib/api/domain-users";
import type { DomainUser, DomainUserListResponse } from "@/types/domain-users";

interface UseDomainUsersOptions {
  /** Initial search query */
  initialQuery?: string;
  /** Items per page (default: 50) */
  limit?: number;
  /** Debounce delay in ms (default: 300) */
  debounceMs?: number;
  /** Whether to fetch on mount (default: true) */
  fetchOnMount?: boolean;
}

interface UseDomainUsersReturn {
  /** List of domain users */
  items: DomainUser[];
  /** Total number of users matching the query */
  total: number;
  /** Whether data is being loaded */
  isLoading: boolean;
  /** Whether initial data is being loaded */
  isInitialLoading: boolean;
  /** Error if fetch failed */
  error: Error | null;
  /** Whether there are more results to fetch */
  hasMore: boolean;
  /** Current page number */
  page: number;
  /** Current search query */
  query: string;
  /** Set search query (triggers debounced fetch) */
  setQuery: (query: string) => void;
  /** Fetch next page of results */
  fetchNextPage: () => Promise<void>;
  /** Reset to first page */
  reset: () => void;
  /** Manually refresh data */
  refresh: () => Promise<void>;
}

/**
 * Hook for fetching and managing domain users with search and pagination.
 *
 * Features:
 * - Server-side search with debouncing
 * - Pagination with "load more" support
 * - In-memory caching of query results
 * - Loading and error states
 *
 * @example
 * ```tsx
 * const { items, isLoading, query, setQuery, fetchNextPage, hasMore } = useDomainUsers({
 *   limit: 50,
 *   debounceMs: 300,
 * });
 * ```
 */
export function useDomainUsers(options: UseDomainUsersOptions = {}): UseDomainUsersReturn {
  const {
    initialQuery = "",
    limit = 50,
    debounceMs = 300,
    fetchOnMount = true,
  } = options;

  // State
  const [items, setItems] = useState<DomainUser[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [page, setPage] = useState(1);
  const [query, setQueryState] = useState(initialQuery);
  const [debouncedQuery, setDebouncedQuery] = useState(initialQuery);

  // Cache for query results (persists during component lifetime)
  const cacheRef = useRef<Map<string, DomainUserListResponse>>(new Map());

  // Debounce timer ref
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Abort controller for cancelling requests
  const abortControllerRef = useRef<AbortController | null>(null);

  // Generate cache key from query params
  const getCacheKey = useCallback((q: string, p: number): string => {
    return `${q}:${p}:${limit}`;
  }, [limit]);

  // Fetch data from API or cache
  const fetchData = useCallback(async (searchQuery: string, pageNum: number, append: boolean = false) => {
    const cacheKey = getCacheKey(searchQuery, pageNum);

    // Check cache first
    const cached = cacheRef.current.get(cacheKey);
    if (cached) {
      if (append) {
        setItems((prev) => [...prev, ...cached.items]);
      } else {
        setItems(cached.items);
      }
      setTotal(cached.total);
      setHasMore(cached.hasMore);
      setPage(pageNum);
      setIsLoading(false);
      setIsInitialLoading(false);
      return;
    }

    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetchDomainUsers({
        q: searchQuery || undefined,
        page: pageNum,
        limit,
      });

      // Cache the response
      cacheRef.current.set(cacheKey, response);

      // Update state
      if (append) {
        setItems((prev) => [...prev, ...response.items]);
      } else {
        setItems(response.items);
      }
      setTotal(response.total);
      setHasMore(response.hasMore);
      setPage(pageNum);
    } catch (err) {
      // Ignore abort errors
      if (err instanceof Error && err.name === "AbortError") {
        return;
      }
      setError(err instanceof Error ? err : new Error("Failed to fetch domain users"));
    } finally {
      setIsLoading(false);
      setIsInitialLoading(false);
    }
  }, [getCacheKey, limit]);

  // Debounced query setter
  const setQuery = useCallback((newQuery: string) => {
    setQueryState(newQuery);

    // Clear existing timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Set new debounce timer
    debounceTimerRef.current = setTimeout(() => {
      setDebouncedQuery(newQuery);
    }, debounceMs);
  }, [debounceMs]);

  // Fetch next page
  const fetchNextPage = useCallback(async () => {
    if (isLoading || !hasMore) return;
    await fetchData(debouncedQuery, page + 1, true);
  }, [isLoading, hasMore, fetchData, debouncedQuery, page]);

  // Reset to first page
  const reset = useCallback(() => {
    setItems([]);
    setTotal(0);
    setPage(1);
    setHasMore(false);
    setQueryState("");
    setDebouncedQuery("");
    cacheRef.current.clear();
  }, []);

  // Manual refresh
  const refresh = useCallback(async () => {
    // Clear cache for current query
    const cacheKey = getCacheKey(debouncedQuery, 1);
    cacheRef.current.delete(cacheKey);
    await fetchData(debouncedQuery, 1, false);
  }, [getCacheKey, debouncedQuery, fetchData]);

  // Fetch when debounced query changes
  useEffect(() => {
    fetchData(debouncedQuery, 1, false);
  }, [debouncedQuery, fetchData]);

  // Initial fetch on mount
  useEffect(() => {
    if (fetchOnMount) {
      fetchData(initialQuery, 1, false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    items,
    total,
    isLoading,
    isInitialLoading,
    error,
    hasMore,
    page,
    query,
    setQuery,
    fetchNextPage,
    reset,
    refresh,
  };
}

// Keep the old export for backwards compatibility
export { useDomainUsers as useAuthUsers };
