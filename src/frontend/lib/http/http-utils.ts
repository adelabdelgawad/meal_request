/**
 * HTTP Utilities - Centralized error normalization, URL resolution, and response mapping
 */

/**
 * Standard API response shape
 */
export interface ApiResponse<T = unknown> {
  ok: boolean;
  message?: string;
  error?: string;
  data?: T;
  status?: number;
}

/**
 * Backend error response shape (from FastAPI HTTPException)
 */
export interface BackendErrorResponse {
  detail?: string;
  message?: string;
  error?: string;
}

/**
 * Normalized error result
 */
export interface ErrorResult {
  ok: false;
  message: string;
  error: string;
  status: number;
}

/**
 * Success result
 */
export interface SuccessResult<T> {
  ok: true;
  data: T;
  status: number;
}

/**
 * Result union type
 */
export type Result<T> = SuccessResult<T> | ErrorResult;

/**
 * Get backend URL from environment or use default
 *
 * Environment variables:
 * - Server-side: BACKEND_API_URL (from .env.local)
 * - Client-side: NEXT_PUBLIC_BACKEND_URL (must be prefixed with NEXT_PUBLIC_)
 *
 * Note: This function is called from server-side API routes,
 * so it uses BACKEND_API_URL which is not exposed to the browser.
 */
export function getBackendUrl(): string {
  // On the server side (API routes)
  if (typeof window === "undefined") {
    const serverUrl = process.env.BACKEND_API_URL;
    if (serverUrl) {
      return serverUrl.replace(/\/$/, "");
    }
    // Default for server-side
    return "http://localhost:8000";
  }

  // On the client side (this shouldn't be called from browser, but handle it)
  // Client-side would need NEXT_PUBLIC_ prefixed variable
  const clientUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
  if (clientUrl) {
    return clientUrl.replace(/\/$/, "");
  }
  return "http://localhost:8000";
}

/**
 * Get API version from environment or use default
 *
 * Environment variables:
 * - Server-side: API_VERSION (from .env.local)
 *
 * Returns the API version prefix (e.g., "v1", "v2")
 * Used to construct versioned endpoints like /v1/login
 */
export function getApiVersion(): string {
  // On the server side (API routes)
  if (typeof window === "undefined") {
    const version = process.env.API_VERSION;
    if (version) {
      // Remove leading slash if present
      return version.replace(/^\//, "");
    }
    // Default version
    return "v1";
  }

  // On the client side (fallback)
  const clientVersion = process.env.NEXT_PUBLIC_API_VERSION;
  if (clientVersion) {
    return clientVersion.replace(/^\//, "");
  }
  return "v1";
}

/**
 * Build versioned API endpoint
 *
 * @param endpoint - The endpoint path (e.g., "/login", "login")
 * @returns Full versioned path (e.g., "/api/v1/login")
 */
export function buildVersionedEndpoint(endpoint: string): string {
  const version = getApiVersion();
  // Remove leading slash from endpoint if present
  const cleanEndpoint = endpoint.replace(/^\//, "");
  return `/api/${version}/${cleanEndpoint}`;
}

/**
 * Normalize error from various sources into a standard error result.
 * Handles FastAPI HTTPException format: { "detail": "..." }
 */
export function normalizeError(
  error: unknown,
  defaultMessage: string = "An unexpected error occurred",
  defaultStatus: number = 500
): ErrorResult {
  let message = defaultMessage;
  let status = defaultStatus;
  let errorCode = "unknown_error";

  // Handle Axios-like error objects
  if (error && typeof error === "object") {
    const err = error as Record<string, unknown>;

    // Check response status
    if (typeof err.status === "number") {
      status = err.status;
    } else if (typeof err.statusCode === "number") {
      status = err.statusCode;
    }

    // Check for FastAPI detail field (HTTPException format: {"detail": "..."})
    // Detail can be a string or an array of validation errors
    if (err.detail) {
      if (typeof err.detail === "string") {
        message = err.detail;
        errorCode = `http_${status}`;
      } else if (Array.isArray(err.detail)) {
        // FastAPI validation errors format
        interface ValidationError {
          loc?: string[];
          msg?: string;
          message?: string;
        }
        const validationErrors = (err.detail as ValidationError[])
          .map((e) => {
            const loc = e.loc ? e.loc.join(" -> ") : "unknown";
            return `${loc}: ${e.msg || e.message || "validation error"}`;
          })
          .join("; ");
        message = `Validation error: ${validationErrors}`;
        errorCode = "validation_error";
      } else {
        message = JSON.stringify(err.detail);
        errorCode = `http_${status}`;
      }
    }
    // Check for standard message field
    else if (typeof err.message === "string") {
      message = err.message;
    }
    // Check for error field
    else if (typeof err.error === "string") {
      message = err.error;
      errorCode = err.error;
    }

    // Map common HTTP status codes to readable error codes
    if (errorCode === "unknown_error" || errorCode.startsWith("http_")) {
      switch (status) {
        case 400:
          errorCode = "bad_request";
          break;
        case 401:
          errorCode = "not_authenticated";
          break;
        case 403:
          errorCode = "forbidden";
          break;
        case 404:
          errorCode = "not_found";
          break;
        case 422:
          errorCode = "validation_error";
          break;
        case 429:
          errorCode = "rate_limited";
          break;
        case 500:
          errorCode = "server_error";
          break;
        case 502:
        case 503:
        case 504:
          errorCode = "service_unavailable";
          break;
      }
    }
  }

  // Handle Error instances
  if (error instanceof Error) {
    message = error.message;
    // Check for specific error types
    if (error.name === "AbortError") {
      status = 504;
      errorCode = "timeout";
      message = "Request timed out. Please try again.";
    }
  }

  // Handle string errors
  if (typeof error === "string") {
    message = error;
  }

  // Enhanced logging for debugging
  console.error("[normalizeError] ❌ Error Details:", {
    status,
    errorCode,
    message,
    originalError:
      error && typeof error === "object"
        ? JSON.stringify(error, null, 2)
        : error,
  });

  return {
    ok: false,
    message,
    error: errorCode,
    status,
  };
}

/**
 * Map response to standard result shape
 */
export function mapResponse<T>(data: unknown, status: number): Result<T> {
  // If data is already a proper response shape
  if (data && typeof data === "object") {
    const response = data as Record<string, unknown>;

    // Check if it's a success response
    if (response.ok === true) {
      return {
        ok: true,
        data: (response.data || response) as T,
        status,
      };
    }

    // Check if it's an error response
    if (response.ok === false) {
      return normalizeError(
        response,
        (response.message as string) || "Request failed",
        status
      );
    }
  }

  // If status indicates success, return data as-is
  if (status >= 200 && status < 300) {
    return {
      ok: true,
      data: data as T,
      status,
    };
  }

  // Otherwise, treat as error
  // console.error("[mapResponse] ❌ Non-2xx status, treating as error", {
  //   status,
  //   responseData:
  //     data && typeof data === "object" ? JSON.stringify(data, null, 2) : data,
  // });
  return normalizeError(data, "Request failed", status);
}

/**
 * Create a timeout-enabled config for HTTP requests
 * - Development: 30 seconds (higher latency when testing from remote hosts)
 * - Production: 10 seconds
 */
export const HTTP_TIMEOUT = process.env.NODE_ENV === 'development' ? 30000 : 10000;

/**
 * Common request headers
 */
export const DEFAULT_HEADERS = {
  "Content-Type": "application/json",
};
