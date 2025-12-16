'use client';

import { useMemo } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, Users, Check, ArrowLeft, ArrowRight, UserPlus } from 'lucide-react';
import { useMealRequest } from '../../context/meal-request-context';
import { useDebouncedState } from '@/hooks/use-debounced-search';
import { useLanguage, translate } from '@/hooks/use-language';
import { MealTypeToggle } from '../meal-type-toggle';
import type { Employee, EmployeesByDepartment } from '@/types/meal-request.types';
import { getLocalizedName } from '@/types/meal-request.types';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

interface EmployeePanelProps {
  employeesByDepartment: EmployeesByDepartment;
}

export function EmployeePanel({ employeesByDepartment }: EmployeePanelProps) {
  const [search, debouncedSearch, setSearch] = useDebouncedState('', 300);
  const { language, t } = useLanguage();
  const {
    selectedDepartments,
    selectedEmployees,
    checkedEmployeeIds,
    setCheckedEmployeeIds,
    notes,
    setNotes,
    addSelectedEmployees,
  } = useMealRequest();

  // Get employees from selected departments
  const availableEmployees = useMemo(() => {
    if (selectedDepartments.length === 0) return [];

    const employees = selectedDepartments.reduce<Employee[]>((acc, dept) => {
      const deptEmployees = employeesByDepartment[dept] || [];
      return [...acc, ...deptEmployees];
    }, []);

    // Filter out already selected employees
    return employees.filter(
      (emp) => !selectedEmployees.some((selected) => selected.id === emp.id)
    );
  }, [selectedDepartments, employeesByDepartment, selectedEmployees]);

  // Filter employees by search term
  const filteredEmployees = useMemo(() => {
    if (!debouncedSearch) return availableEmployees;

    const searchTerms = debouncedSearch
      .split(/[\s,]+/)
      .map((term) => term.trim().toLowerCase())
      .filter(Boolean);

    if (searchTerms.length === 0) return availableEmployees;

    return availableEmployees.filter((emp) =>
      searchTerms.some(
        (term) =>
          String(emp.code).toLowerCase().includes(term) ||
          emp.nameEn?.toLowerCase().includes(term) ||
          emp.nameAr?.toLowerCase().includes(term) ||
          emp.title?.toLowerCase().includes(term)
      )
    );
  }, [availableEmployees, debouncedSearch]);

  // Get the correct arrow icon based on language direction
  const ArrowIcon = language === 'ar' ? ArrowLeft : ArrowRight;

  const handleToggleEmployee = (employeeId: number) => {
    const newChecked = new Set(checkedEmployeeIds);
    if (newChecked.has(employeeId)) {
      newChecked.delete(employeeId);
    } else {
      newChecked.add(employeeId);
    }
    setCheckedEmployeeIds(newChecked);
  };

  const handleAddSelected = () => {
    if (checkedEmployeeIds.size === 0) {
      toast.error(translate(t, 'mealRequest.toast.selectAtLeastOne'));
      return;
    }

    const employeesToAdd = filteredEmployees.filter((emp) =>
      checkedEmployeeIds.has(emp.id)
    );

    addSelectedEmployees(employeesToAdd);
    toast.success(
      `${employeesToAdd.length} ${translate(t, 'mealRequest.toast.employeeAdded')}`
    );
  };

  return (
    <div className="flex flex-col h-full">
      {/* Compact Header Row: Title + Meal Type + Notes */}
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <div className="flex items-center gap-2 me-auto">
          <div className="p-1.5 rounded-md bg-emerald-100 dark:bg-emerald-900/50">
            <Users className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
          </div>
          <span className="text-sm font-medium">
            {filteredEmployees.length} {translate(t, 'mealRequest.employees.available')}
            {checkedEmployeeIds.size > 0 && (
              <span className="text-emerald-600 dark:text-emerald-400">
                {' '}({checkedEmployeeIds.size} {translate(t, 'mealRequest.employees.checked')})
              </span>
            )}
          </span>
        </div>
        <MealTypeToggle />
      </div>

      {/* Search + Notes + Add Button Row */}
      <div className="flex gap-2 mb-2">
        <div className="relative flex-[3]">
          <Search className="absolute start-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={translate(t, 'mealRequest.employees.search')}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="ps-9 bg-muted/50 h-9"
          />
        </div>
        <Input
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder={translate(t, 'mealRequest.employees.notePlaceholder')}
          className="flex-[2] bg-muted/50 h-9"
        />
        <Button
          onClick={handleAddSelected}
          disabled={checkedEmployeeIds.size === 0}
          size="sm"
          className="gap-1.5 h-9"
        >
          {translate(t, 'mealRequest.employees.add')}
          <ArrowIcon className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Employee List */}
      <div className="flex-1 min-h-0 overflow-auto -mx-1 px-1">
        <div className="space-y-1.5 pe-1">
          {selectedDepartments.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="p-4 rounded-full bg-muted/50 mb-3">
                <Users className="h-10 w-10 text-muted-foreground/30" />
              </div>
              <p className="text-sm font-medium text-muted-foreground">{translate(t, 'mealRequest.employees.noDepartmentsSelected')}</p>
              <p className="text-xs text-muted-foreground/70 mt-1">
                {translate(t, 'mealRequest.employees.selectDepartmentsFirst')}
              </p>
            </div>
          )}
          {selectedDepartments.length > 0 && filteredEmployees.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="p-4 rounded-full bg-muted/50 mb-3">
                <UserPlus className="h-10 w-10 text-muted-foreground/30" />
              </div>
              <p className="text-sm font-medium text-muted-foreground">{translate(t, 'mealRequest.employees.noEmployees')}</p>
              <p className="text-xs text-muted-foreground/70 mt-1">
                {translate(t, 'mealRequest.employees.tryDifferentSearch')}
              </p>
            </div>
          )}
          {filteredEmployees.map((emp) => {
            const isChecked = checkedEmployeeIds.has(emp.id);
            return (
              <button
                key={emp.id}
                type="button"
                onClick={() => handleToggleEmployee(emp.id)}
                className={cn(
                  'w-full flex items-center gap-3 p-3 rounded-lg border transition-all duration-200 text-start',
                  'focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-primary/50',
                  isChecked
                    ? 'border-emerald-500 dark:border-emerald-600 bg-emerald-50 dark:bg-emerald-950/50 shadow-sm'
                    : 'border-transparent bg-muted/40 hover:bg-muted/80 hover:border-border'
                )}
              >
                <div
                  className={cn(
                    'flex items-center justify-center w-5 h-5 rounded-md border-2 transition-colors shrink-0',
                    isChecked
                      ? 'bg-emerald-500 border-emerald-500 dark:bg-emerald-600 dark:border-emerald-600'
                      : 'border-muted-foreground/30 bg-background'
                  )}
                >
                  {isChecked && <Check className="h-3 w-3 text-white" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        'text-xs font-mono px-1.5 py-0.5 rounded',
                        isChecked
                          ? 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300'
                          : 'bg-muted text-muted-foreground'
                      )}
                    >
                      {emp.code}
                    </span>
                    <span
                      className={cn(
                        'text-sm truncate',
                        isChecked ? 'font-medium text-foreground' : 'text-muted-foreground'
                      )}
                    >
                      {getLocalizedName(emp.nameEn, emp.nameAr, language)}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground/70 truncate mt-0.5">
                    {emp.title}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
