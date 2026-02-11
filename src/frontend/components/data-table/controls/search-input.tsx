 
"use client";

import React, { useTransition, useState, useEffect } from "react";
import { Search, X } from "lucide-react";
import { useQueryState, parseAsString } from "nuqs";

interface SearchInputProps {
  placeholder?: string;
  className?: string;
  urlParam?: string;
  debounceMs?: number;
}

export const SearchInput: React.FC<SearchInputProps> = ({
  placeholder = "Search...",
  className = "",
  urlParam = "filter",
  debounceMs = 2000,
}) => {
  const [urlValue, setUrlValue] = useQueryState(
    urlParam,
    parseAsString.withDefault("")
  );
  const [isPending, startTransition] = useTransition();
  
  // Local state for immediate UI updates
  const [localValue, setLocalValue] = useState(urlValue);
  const [isDebouncing, setIsDebouncing] = useState(false);

  // Sync local value with URL value when URL changes externally
  useEffect(() => {
    setLocalValue(urlValue);
  }, [urlValue]);

  // Debounced update to URL
  useEffect(() => {
    if (localValue === urlValue) {
      setIsDebouncing(false);
      return;
    }

    setIsDebouncing(true);
    const timer = setTimeout(() => {
      startTransition(() => {
        setUrlValue(localValue || null);
        setIsDebouncing(false);
      });
    }, debounceMs);

    return () => {
      clearTimeout(timer);
    };
  }, [localValue, debounceMs, setUrlValue, urlValue]);

  const handleChange = (newValue: string) => {
    setLocalValue(newValue);
  };

  const handleClear = () => {
    setLocalValue("");
    startTransition(() => {
      setUrlValue(null);
    });
  };

  const showLoading = isPending || isDebouncing;

  return (
    <div className={`relative flex-1 max-w-md ${className}`}>
      <Search className="absolute start-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
      <input
        type="text"
        value={localValue}
        onChange={(e) => handleChange(e.target.value)}
        placeholder={placeholder}
        className="w-full ps-10 pe-10 py-2 border border-input bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
      />
      <div className="absolute end-3 top-1/2 transform -translate-y-1/2 flex items-center gap-2">
        {localValue && (
          <button
            onClick={handleClear}
            className="text-muted-foreground hover:text-foreground transition-colors"
            type="button"
          >
            <X className="w-4 h-4" />
          </button>
        )}
        {showLoading && (
          <div className="w-4 h-4 border-2 border-muted border-t-primary animate-spin" />
        )}
      </div>
    </div>
  );
};