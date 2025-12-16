/**
 * Server-side Axios HTTP connector
 * Used in server actions and API routes to communicate directly with the backend
 */

import axios, { AxiosInstance, AxiosRequestConfig } from "axios";
import { cookies } from "next/headers";
import {
  getBackendUrl,
  buildVersionedEndpoint,
  normalizeError,
  mapResponse,
  Result,
  HTTP_TIMEOUT,
  DEFAULT_HEADERS,
} from "./http-utils";

/**
 * Initialize a fresh Axios instance for each request
 * (Don't cache - each request may have different cookies)
 */
function getAxiosInstance(): AxiosInstance {
  return axios.create({
    baseURL: getBackendUrl(),
    timeout: HTTP_TIMEOUT,
    headers: DEFAULT_HEADERS,
    validateStatus: () => true, // Don't throw on any status code
  });
}

/**
 * Make a server-side request and return normalized result
 *
 * Note: API versioning is available but disabled by default.
 * The backend currently uses non-versioned endpoints (/login, /refresh, etc)
 * To enable versioning, set useVersioning: true in options.
 */
export async function serverRequest<T>(
  method: "get" | "post" | "put" | "patch" | "delete",
  endpoint: string,
  options?: {
    data?: unknown;
    params?: Record<string, unknown>;
    headers?: Record<string, string>;
    useVersioning?: boolean; // Set to true to enable versioning (/v1/login)
  }
): Promise<Result<T> & { headers?: Record<string, string> }> {
  try {
    const instance = getAxiosInstance();

    // Build versioned endpoint only if explicitly enabled
    const finalEndpoint = options?.useVersioning
      ? buildVersionedEndpoint(endpoint)
      : endpoint;

    // Forward all cookies from Next.js request to backend
    const cookieStore = await cookies();
    const allCookies = cookieStore.getAll();

    const requestHeaders: Record<string, string> = {
      ...options?.headers,
    };

    // Build cookie header string from all cookies
    if (allCookies.length > 0) {
      const cookieHeader = allCookies
        .map(c => `${c.name}=${c.value}`)
        .join('; ');
      requestHeaders['Cookie'] = cookieHeader;
    }

    const config: AxiosRequestConfig = {
      method,
      url: finalEndpoint,
      headers: requestHeaders,
      params: options?.params,
    };

    if (options?.data) {
      config.data = options.data;
    }

    const response = await instance.request(config);

    // Log request details for debugging
    console.log(`[axios-server] Request completed [${method.toUpperCase()} ${finalEndpoint}]`, {
      status: response.status,
      statusText: response.statusText,
    });

    // Log full response for non-2xx status codes
    if (response.status < 200 || response.status >= 300) {
      console.error(`[axios-server] ❌ Error Response [${method.toUpperCase()} ${finalEndpoint}]`, {
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
        data: response.data,
        requestData: options?.data,
        requestParams: options?.params,
      });
    }

    // Map the response to standard result shape and include headers
    const result = mapResponse<T>(response.data, response.status);
    return {
      ...result,
      headers: response.headers as Record<string, string>,
    };
  } catch (error) {
    console.error(`[axios-server] ❌ Request failed [${method.toUpperCase()} ${endpoint}]`, {
      error,
      errorMessage: error instanceof Error ? error.message : String(error),
      errorStack: error instanceof Error ? error.stack : undefined,
    });
    return normalizeError(error, "Server request failed") as Result<T> & { headers?: Record<string, string> };
  }
}

/**
 * Convenience methods for common HTTP verbs
 */
export const serverApi = {
  get: <T,>(endpoint: string, options?: Parameters<typeof serverRequest>[2]) =>
    serverRequest<T>("get", endpoint, options),

  post: <T,>(
    endpoint: string,
    data?: unknown,
    options?: Omit<Parameters<typeof serverRequest>[2], "data">
  ) => serverRequest<T>("post", endpoint, { ...options, data }),

  put: <T,>(
    endpoint: string,
    data?: unknown,
    options?: Omit<Parameters<typeof serverRequest>[2], "data">
  ) => serverRequest<T>("put", endpoint, { ...options, data }),

  patch: <T,>(
    endpoint: string,
    data?: unknown,
    options?: Omit<Parameters<typeof serverRequest>[2], "data">
  ) => serverRequest<T>("patch", endpoint, { ...options, data }),

  delete: <T,>(endpoint: string, options?: Parameters<typeof serverRequest>[2]) =>
    serverRequest<T>("delete", endpoint, options),
};
