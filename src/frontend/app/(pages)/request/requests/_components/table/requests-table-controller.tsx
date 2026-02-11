"use client";

import { Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useState, useEffect, startTransition } from "react";
import { DynamicTableBar } from "@/components/data-table/table/data-table-bar";
import { RequestsDateRangePicker } from "../controls/date-range-picker";
import { LiveIndicator } from "../live-indicator";
import { useLanguage } from "@/hooks/use-language";

interface RequestsTableControllerProps {
  fromDate: string;
  toDate: string;
  requesterFilter: string;
  isLive: boolean;
  isValidating?: boolean;
  hasActiveFilters?: boolean;
  onFromDateChange: (value: string) => void;
  onToDateChange: (value: string) => void;
  onRequesterChange: (value: string) => void;
}

/**
 * Controller section for the requests table with search, date filters, and live indicator
 */
export function RequestsTableController({
  fromDate,
  toDate,
  requesterFilter,
  isLive,
  isValidating = false,
  hasActiveFilters = false,
  onFromDateChange,
  onToDateChange,
  onRequesterChange,
}: RequestsTableControllerProps) {
  const { t, language } = useLanguage();
  const isRtl = language === "ar";

  // Get translations
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const filters = ((t?.requests as Record<string, unknown>)?.filters || {}) as any;

  // Local state for debounced requester input
  const [localRequester, setLocalRequester] = useState(requesterFilter);

  // Sync local state when prop changes (e.g., from URL)
  useEffect(() => {
    startTransition(() => setLocalRequester(requesterFilter));
  }, [requesterFilter]);

  // Debounce the requester filter
  useEffect(() => {
    const timer = setTimeout(() => {
      if (localRequester !== requesterFilter) {
        onRequesterChange(localRequester);
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [localRequester, requesterFilter, onRequesterChange]);

  const hasFilters = fromDate || toDate || requesterFilter;

  const clearAllFilters = () => {
    setLocalRequester("");
    onFromDateChange("");
    onToDateChange("");
    onRequesterChange("");
  };

  return (
    <div className="shrink-0">
      <DynamicTableBar
        variant="controller"
        left={
          <div className="relative flex-1 min-w-[200px] max-w-[320px]">
            <Search
              className={`absolute top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground ${
                isRtl ? "right-3" : "left-3"
              }`}
            />
            <Input
              type="text"
              placeholder={filters.searchByName || "Search by requester..."}
              value={localRequester}
              onChange={(e) => setLocalRequester(e.target.value)}
              className={`h-9 ${isRtl ? "pr-10 pl-8" : "pl-10 pr-8"}`}
            />
            {localRequester && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setLocalRequester("");
                  onRequesterChange("");
                }}
                className={`absolute top-1/2 -translate-y-1/2 h-8 w-8 p-0 ${
                  isRtl ? "left-1" : "right-1"
                }`}
              >
                <X className="h-3 w-3" />
              </Button>
            )}
          </div>
        }
        right={
          <>
            <RequestsDateRangePicker
              startTime={fromDate}
              endTime={toDate}
              onStartTimeChange={onFromDateChange}
              onEndTimeChange={onToDateChange}
            />
            {hasFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearAllFilters}
                className="h-9 text-xs text-muted-foreground hover:text-foreground whitespace-nowrap"
              >
                <X className="h-3 w-3 me-1" />
                {filters.clearAll || "Clear all"}
              </Button>
            )}
            <LiveIndicator
              isLive={isLive}
              isValidating={isValidating}
              filtersActive={hasActiveFilters}
            />
          </>
        }
      />
    </div>
  );
}
