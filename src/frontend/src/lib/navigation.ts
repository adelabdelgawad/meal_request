/**
 * Navigation Module
 *
 * Functions:
 * - getNavigation() - Fetch permission-aware navigation tree
 */

import { apiFetch } from './api-client';
import type { NavigationResponse } from '@/src/types/navigation.types';

/**
 * Get navigation tree
 *
 * @param navType - Optional filter by navigation type (e.g., 'main', 'sidebar', 'footer')
 * @returns Navigation tree with hierarchical structure
 */
export async function getNavigation(navType?: string): Promise<NavigationResponse> {
  const params = navType ? `?navType=${encodeURIComponent(navType)}` : '';
  return apiFetch<NavigationResponse>(`/navigation${params}`);
}
