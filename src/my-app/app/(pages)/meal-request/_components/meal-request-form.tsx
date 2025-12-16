'use client';

import { useMemo } from 'react';
import { DepartmentPanel } from './department-panel/department-panel';
import { EmployeePanel } from './employee-panel/employee-panel';
import { SelectedPanel } from './selected-panel/selected-panel';
import { SubmitSection } from './submit-section';
import { StatsHeader } from './stats-header';
import type { EmployeesByDepartment } from '@/types/meal-request.types';

interface MealRequestFormProps {
  initialEmployees: EmployeesByDepartment;
}

export function MealRequestForm({ initialEmployees }: MealRequestFormProps) {
  // Extract unique departments
  const departments = useMemo(() => {
    return Object.keys(initialEmployees).sort();
  }, [initialEmployees]);

  return (
    <div className="flex flex-col flex-1 min-h-0 gap-2">
      {/* Stats Header */}
      <StatsHeader totalDepartments={departments.length} />

      {/* Three Column Layout - Optimized for mobile */}
      <div className="flex flex-col lg:flex-row gap-1.5 flex-1 min-h-0 overflow-hidden">
        {/* Left Column - Departments */}
        <div className="flex-[2] bg-card border rounded-xl p-3 min-h-[200px] lg:min-h-0 shadow-sm overflow-hidden">
          <DepartmentPanel departments={departments} employeesByDepartment={initialEmployees} />
        </div>

        {/* Center Column - Meal Type & Employees */}
        <div className="flex-[3] bg-card border rounded-xl p-3 min-h-[200px] lg:min-h-0 shadow-sm overflow-hidden">
          <EmployeePanel employeesByDepartment={initialEmployees} />
        </div>

        {/* Right Column - Selected */}
        <div className="flex-[3] bg-card border rounded-xl p-3 min-h-[200px] lg:min-h-0 shadow-sm overflow-hidden">
          <SelectedPanel />
        </div>
      </div>

      {/* Submit Section */}
      <SubmitSection />
    </div>
  );
}
