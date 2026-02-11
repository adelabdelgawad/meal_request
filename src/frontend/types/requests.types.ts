export type RequestStatus = 'Pending' | 'Approved' | 'Rejected';

export interface RequestsFilters {
  status?: RequestStatus | 'Any';
  fromDate?: string;
  toDate?: string;
  requesterSearch?: string;
  page?: number;
  limit?: number;
}

export interface RequestsResponse {
  data: import('./meal-request.types').MealRequest[];
  total: number;
  page: number;
  limit: number;
}

export interface UpdateMealRequestPayload {
  mealRequestId: number;
  statusId: number; // 2 = Approved, 3 = Rejected
  accountId: number;
}
