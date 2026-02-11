export interface EmployeeAnalytics {
  name: string;
  acceptedRequests: number;
}

export interface AnalyticsResponse {
  data: EmployeeAnalytics[];
  total: number;
}

export interface AuditRecord extends Record<string, unknown> {
  code: string;
  employeeNameEn: string;
  employeeNameAr: string;
  title: string;
  departmentEn: string;
  departmentAr: string;
  requesterEn: string;
  requesterAr: string;
  requesterTitle: string;
  requestTime: string;
  mealTypeEn: string;
  mealTypeAr: string;
  inTime: string | null;
  outTime: string | null;
  workingHours: number | null;
  notes: string | null;
}

export interface AuditFilters {
  startTime: string;
  endTime: string;
}

export interface AnalyticsFilters {
  startTime: string;
  endTime: string;
}
