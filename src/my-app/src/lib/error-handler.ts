/**
 * Centralized Error Handler
 *
 * Functions:
 * - handleApiError() - Handle API errors with user-friendly messages
 */

import { ApiError } from '@/src/types/error.types';

/**
 * Show toast notification
 * Note: Replace with your actual toast implementation
 */
function showToast(options: {
  title: string;
  description?: string;
  variant?: 'default' | 'destructive';
  action?: { label: string; onClick: () => void };
}) {
  // TODO: Replace with your actual toast implementation
  // For now, just console.log
  console.error(`[Toast] ${options.title}`, options.description);
  if (options.action) {
    console.log(`[Toast Action] ${options.action.label}`);
  }
}

/**
 * Handle API errors with user-friendly messages
 */
export function handleApiError(error: unknown): void {
  if (error instanceof ApiError) {
    switch (error.statusCode) {
      case 401:
        showToast({
          title: 'Session expired',
          description: 'Please log in again',
          variant: 'destructive',
          action: {
            label: 'Login',
            onClick: () => {
              if (typeof window !== 'undefined') {
                window.location.href = '/login';
              }
            },
          },
        });
        break;

      case 403:
        showToast({
          title: 'Access denied',
          description: 'You do not have permission to perform this action',
          variant: 'destructive',
        });
        break;

      case 429:
        showToast({
          title: 'Too many requests',
          description: 'Please slow down and try again later',
          variant: 'destructive',
        });
        break;

      case 500:
        showToast({
          title: 'Server error',
          description: 'Something went wrong on our end. Please try again',
          variant: 'destructive',
        });
        break;

      default:
        showToast({
          title: 'Error',
          description: error.message || 'An unexpected error occurred',
          variant: 'destructive',
        });
    }
  } else if (error instanceof Error) {
    // Network or other errors
    if (error.name === 'AbortError') {
      showToast({
        title: 'Request timeout',
        description: 'The request took too long. Please try again',
        variant: 'destructive',
      });
    } else if (error.message.includes('NetworkError') || error.message.includes('fetch')) {
      showToast({
        title: 'Network error',
        description: 'Please check your internet connection and try again',
        variant: 'destructive',
        action: {
          label: 'Retry',
          onClick: () => window.location.reload(),
        },
      });
    } else {
      showToast({
        title: 'Error',
        description: error.message,
        variant: 'destructive',
      });
    }
  } else {
    showToast({
      title: 'Unknown error',
      description: 'An unexpected error occurred',
      variant: 'destructive',
    });
  }
}
