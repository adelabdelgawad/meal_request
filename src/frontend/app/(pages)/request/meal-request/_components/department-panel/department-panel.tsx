'use client';

import { useMemo } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, Building2, Check, CheckCheck, X } from 'lucide-react';
import { useMealRequest } from '../../context/meal-request-context';
import { useDebouncedState } from '@/hooks/use-debounced-search';
import { useLanguage, translate } from '@/hooks/use-language';
import { cn } from '@/lib/utils';
import type { EmployeesByDepartment } from '@/types/meal-request.types';

interface DepartmentPanelProps {
  departments: string[];
  employeesByDepartment: EmployeesByDepartment;
}

export function DepartmentPanel({ departments, employeesByDepartment }: DepartmentPanelProps) {
  const [search, debouncedSearch, setSearch] = useDebouncedState('', 300);
  const { selectedDepartments, setSelectedDepartments } = useMealRequest();
  const { language, t } = useLanguage();

  // Build a map of department English name to Arabic name for display
  const departmentNames = useMemo(() => {
    const names: Record<string, { en: string; ar: string | null }> = {};
    for (const deptKey of departments) {
      const employees = employeesByDepartment[deptKey];
      if (employees && employees.length > 0) {
        names[deptKey] = {
          en: employees[0].departmentEn || deptKey,
          ar: employees[0].departmentAr,
        };
      } else {
        names[deptKey] = { en: deptKey, ar: null };
      }
    }
    return names;
  }, [departments, employeesByDepartment]);

  // Get localized department name
  const getLocalizedDeptName = (deptKey: string) => {
    const names = departmentNames[deptKey];
    if (!names) return deptKey;
    if (language === 'ar') {
      return names.ar || names.en;
    }
    return names.en;
  };

  const filteredDepartments = useMemo(() => {
    if (!debouncedSearch) return departments;
    const searchLower = debouncedSearch.toLowerCase();
    return departments.filter((deptKey) => {
      const names = departmentNames[deptKey];
      // Search in both English and Arabic names
      return (
        deptKey.toLowerCase().includes(searchLower) ||
        names?.en?.toLowerCase().includes(searchLower) ||
        names?.ar?.toLowerCase().includes(searchLower)
      );
    });
  }, [departments, debouncedSearch, departmentNames]);

  const handleSelectAll = () => {
    setSelectedDepartments(filteredDepartments);
  };

  const handleRemoveAll = () => {
    setSelectedDepartments([]);
  };

  const handleToggleDepartment = (dept: string) => {
    if (selectedDepartments.includes(dept)) {
      setSelectedDepartments(selectedDepartments.filter((d) => d !== dept));
    } else {
      setSelectedDepartments([...selectedDepartments, dept]);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Compact Header */}
      <div className="flex items-center gap-2 mb-2">
        <div className="p-1.5 rounded-md bg-blue-100 dark:bg-blue-900/50">
          <Building2 className="h-4 w-4 text-blue-600 dark:text-blue-400" />
        </div>
        <span className="text-sm font-medium">
          {selectedDepartments.length}/{departments.length} {translate(t, 'mealRequest.departments.depts')}
        </span>
        <div className="flex gap-1 ms-auto">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleSelectAll}
            className="h-7 px-2 text-xs"
          >
            <CheckCheck className="h-3 w-3 me-1" />
            {translate(t, 'mealRequest.departments.selectAll')}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRemoveAll}
            className="h-7 px-2 text-xs"
          >
            <X className="h-3 w-3 me-1" />
            {translate(t, 'mealRequest.selected.clear')}
          </Button>
        </div>
      </div>

      <div className="relative mb-2">
        <Search className="absolute start-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder={translate(t, 'mealRequest.departments.search')}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="ps-9 bg-muted/50 h-9"
        />
      </div>

      <div className="flex-1 min-h-0 overflow-auto -mx-1 px-1">
        <div className="space-y-1.5 pe-1">
          {filteredDepartments.map((deptKey) => {
            const isSelected = selectedDepartments.includes(deptKey);
            return (
              <button
                key={deptKey}
                type="button"
                onClick={() => handleToggleDepartment(deptKey)}
                className={cn(
                  'w-full flex items-center gap-3 p-3 rounded-lg border transition-all duration-200',
                  'focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-primary/50',
                  isSelected
                    ? 'border-blue-500 dark:border-blue-600 bg-blue-50 dark:bg-blue-950/50 shadow-sm'
                    : 'border-transparent bg-muted/40 hover:bg-muted/80 hover:border-border'
                )}
              >
                <div
                  className={cn(
                    'flex items-center justify-center w-5 h-5 rounded-md border-2 transition-colors',
                    isSelected
                      ? 'bg-blue-500 border-blue-500 dark:bg-blue-600 dark:border-blue-600'
                      : 'border-muted-foreground/30 bg-background'
                  )}
                >
                  {isSelected && <Check className="h-3 w-3 text-white" />}
                </div>
                <span
                  className={cn(
                    'text-sm text-start flex-1 truncate',
                    isSelected ? 'font-medium text-foreground' : 'text-muted-foreground'
                  )}
                >
                  {getLocalizedDeptName(deptKey)}
                </span>
              </button>
            );
          })}
          {filteredDepartments.length === 0 && (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <Building2 className="h-10 w-10 text-muted-foreground/30 mb-2" />
              <p className="text-sm text-muted-foreground">{translate(t, 'mealRequest.departments.noDepartments')}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
