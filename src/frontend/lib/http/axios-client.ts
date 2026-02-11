/**
 * Client-side Axios HTTP connector
 * Used in browser to communicate with Next.js API routes (which internally call the backend)
 */

import axios, { AxiosInstance, AxiosRequestConfig } from "axios";
import { normalizeError, mapResponse, Result, HTTP_TIMEOUT, DEFAULT_HEADERS } from "./http-utils";

let axiosInstance: AxiosInstance | null = null;

/**
 * Initialize or get the client-side Axios instance
 * Base URL is the Next.js app itself (not the backend directly)
 */
function getAxiosInstance(): AxiosInstance {
  if (!axiosInstance) {
    axiosInstance = axios.create({
      baseURL: "/api",
      timeout: HTTP_TIMEOUT,
      headers: DEFAULT_HEADERS,
      validateStatus: () => true, // Don't throw on any status code
    });
  }
  return axiosInstance;
}

/**
 * Make a client-side request and return normalized result
 */
export async function clientRequest<T>(
  method: "get" | "post" | "put" | "patch" | "delete",
  endpoint: string,
  options?: {
    data?: unknown;
    params?: Record<string, unknown>;
    headers?: Record<string, string>;
  }
): Promise<Result<T>> {
  try {
    const instance = getAxiosInstance();
    const config: AxiosRequestConfig = {
      method,
      url: endpoint,
      headers: options?.headers,
      params: options?.params,
    };

    if (options?.data) {
      config.data = options.data;
    }

    const response = await instance.request(config);

    // Map the response to standard result shape
    return mapResponse<T>(response.data, response.status);
  } catch (error) {
    console.error(`Client request failed [${method.toUpperCase()} ${endpoint}]:`, error);
    return normalizeError(error, "Client request failed") as Result<T>;
  }
}

/**
 * Convenience methods for common HTTP verbs
 */
export const clientApi = {
  get: <T,>(endpoint: string, options?: Parameters<typeof clientRequest>[2]) =>
    clientRequest<T>("get", endpoint, options),

  post: <T,>(
    endpoint: string,
    data?: unknown,
    options?: Omit<Parameters<typeof clientRequest>[2], "data">
  ) => clientRequest<T>("post", endpoint, { ...options, data }),

  put: <T,>(
    endpoint: string,
    data?: unknown,
    options?: Omit<Parameters<typeof clientRequest>[2], "data">
  ) => clientRequest<T>("put", endpoint, { ...options, data }),

  patch: <T,>(
    endpoint: string,
    data?: unknown,
    options?: Omit<Parameters<typeof clientRequest>[2], "data">
  ) => clientRequest<T>("patch", endpoint, { ...options, data }),

  delete: <T,>(endpoint: string, options?: Parameters<typeof clientRequest>[2]) =>
    clientRequest<T>("delete", endpoint, options),
};
