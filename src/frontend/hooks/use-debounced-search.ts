import { useState, useEffect, useCallback } from "react";

/**
 * Hook that returns a debounced state value
 * @param initialValue - Initial value
 * @param delay - Debounce delay in milliseconds
 */
export function useDebouncedState<T>(
  initialValue: T,
  delay: number = 300
): [T, T, (value: T) => void] {
  const [value, setValue] = useState<T>(initialValue);
  const [debouncedValue, setDebouncedValue] = useState<T>(initialValue);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  const setValueCallback = useCallback((newValue: T) => {
    setValue(newValue);
  }, []);

  return [value, debouncedValue, setValueCallback];
}

/**
 * Hook that returns only a debounced value
 * @param value - Value to debounce
 * @param delay - Debounce delay in milliseconds
 */
export function useDebouncedValue<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}
