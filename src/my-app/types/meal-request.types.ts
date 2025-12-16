// Meal type
export interface MealType {
  id: number;
  nameEn: string;
  nameAr: string;
  priority: number;
  isActive: boolean;
  isDeleted: boolean;
  createdAt: string;
  updatedAt: string;
  createdById?: string | null;
  updatedById?: string | null;
}

// Employee types
export interface Employee {
  id: number;
  code: string;
  nameEn: string | null;
  nameAr: string | null;
  title: string | null;
  departmentId: number;
  departmentEn: string | null;
  departmentAr: string | null;
}

export interface EmployeesByDepartment {
  [departmentName: string]: Employee[];
}

// Meal request types
export interface MealRequestLine {
  employeeId: number;
  employeeCode: string;
  notes: string;
}

export interface CreateMealRequestPayload {
  requesterId: number;
  mealTypeId: number;
  requestLines: MealRequestLine[];
}

export interface MealRequest {
  mealRequestId: number;
  requesterName: string;
  requesterTitle: string;
  requestTime: string;
  closedTime: string | null;
  notes: string | null;
  mealTypeEn: string;
  mealTypeAr: string;
  totalRequestLines: number;
  acceptedRequestLines: number;
  statusNameEn: 'Pending' | 'Approved' | 'Rejected';
  statusNameAr: 'قيد الانتظار' | 'مقبول' | 'مرفوض';
  statusId: number;
}

export interface RequestLine {
  requestLineId: number;
  code: string;
  nameEn: string | null;
  nameAr: string | null;
  title: string | null;
  departmentEn: string | null;
  departmentAr: string | null;
  shiftHours: string;
  signInTime: string | null;
  mealType: string;
  accepted: boolean;
  notes: string | null;
}

export interface UpdateRequestLinePayload {
  userId: string;
  mealRequestLineId: number;
  accepted: boolean;
  notes: string;
}

// Selected employee for form
export interface SelectedEmployee extends Employee {
  note: string;
  mealType: string; // Meal type ID as string for form compatibility
}

// Helper function to get localized name
export function getLocalizedName(
  nameEn: string | null | undefined,
  nameAr: string | null | undefined,
  locale: string = 'en'
): string {
  if (locale === 'ar') {
    return nameAr || nameEn || '';
  }
  return nameEn || nameAr || '';
}

// Helper function to get localized meal type name
export function getMealTypeName(
  mealType: MealType,
  locale: string = 'en'
): string {
  return getLocalizedName(mealType.nameEn, mealType.nameAr, locale);
}

// Status IDs for meal requests
export const REQUEST_STATUS_IDS = {
  PENDING: 1,
  APPROVED: 2,
  REJECTED: 3,
} as const;

// Status badge colors (light and dark mode)
export const REQUEST_STATUS_COLORS: Record<string, string> = {
  Pending: 'bg-yellow-200 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  Approved: 'bg-green-200 text-green-800 dark:bg-green-900 dark:text-green-200',
  Rejected: 'bg-red-200 text-red-800 dark:bg-red-900 dark:text-red-200',
};

// Meal request statistics
export interface MealRequestStats {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
}

// Paginated response with unified stats
export interface PaginatedMealRequests {
  items: MealRequest[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  stats: MealRequestStats;
}

// Status option
export interface MealRequestStatusOption {
  id: number;
  nameEn: string;
  nameAr: string;
  isActive: boolean;
}

// Response from copy request endpoint
export interface CopyMealRequestResponse {
  message: string;
  originalRequestId: number;
  newMealRequestId: number;
  linesCopied: number;
  mealTypeId: number;
}
