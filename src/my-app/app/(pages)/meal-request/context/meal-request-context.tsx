'use client';

import { createContext, useContext, useState, ReactNode } from 'react';
import type { Employee, SelectedEmployee, MealType } from '@/types/meal-request.types';

interface MealRequestContextType {
  mealTypes: MealType[];
  selectedDepartments: string[];
  setSelectedDepartments: (deps: string[]) => void;
  selectedEmployees: SelectedEmployee[];
  setSelectedEmployees: (emps: SelectedEmployee[]) => void;
  checkedEmployeeIds: Set<number>;
  setCheckedEmployeeIds: (ids: Set<number>) => void;
  selectedMealTypes: Set<string>;
  toggleMealType: (type: string) => void;
  notes: string;
  setNotes: (notes: string) => void;
  addSelectedEmployees: (employees: Employee[]) => void;
  removeSelectedEmployee: (employeeId: number, mealType?: string) => void;
  removeAllSelectedEmployees: () => void;
}

const MealRequestContext = createContext<MealRequestContextType | null>(null);

export function MealRequestProvider({
  children,
  mealTypes = []
}: {
  children: ReactNode;
  mealTypes?: MealType[];
}) {
  const [selectedDepartments, setSelectedDepartments] = useState<string[]>([]);
  const [selectedEmployees, setSelectedEmployees] = useState<SelectedEmployee[]>([]);
  const [checkedEmployeeIds, setCheckedEmployeeIds] = useState<Set<number>>(new Set());

  // Initialize with highest priority meal type (already sorted by backend with priority DESC)
  // Backend returns meal types sorted by priority descending, so first one has highest priority
  const [selectedMealTypes, setSelectedMealTypes] = useState<Set<string>>(
    () => new Set(mealTypes.length > 0 ? [mealTypes[0].id.toString()] : [])
  );
  const [notes, setNotes] = useState('');


  // Toggle meal type selection
  const toggleMealType = (type: string) => {
    const newSet = new Set(selectedMealTypes);
    if (newSet.has(type)) {
      // Don't allow deselecting if it's the only one selected
      if (newSet.size > 1) {
        newSet.delete(type);
      }
    } else {
      newSet.add(type);
    }
    setSelectedMealTypes(newSet);
  };

  // Add checked employees to selected list - one entry per meal type
  const addSelectedEmployees = (employees: Employee[]) => {
    const mealTypes = Array.from(selectedMealTypes);
    const newSelected: SelectedEmployee[] = [];

    employees.forEach((emp) => {
      mealTypes.forEach((mealType) => {
        // Check if this employee + meal type combo already exists
        const exists = selectedEmployees.some(
          (s) => s.id === emp.id && s.mealType === mealType
        );
        if (!exists) {
          newSelected.push({
            ...emp,
            mealType,
            note: notes,
          });
        }
      });
    });

    setSelectedEmployees([...selectedEmployees, ...newSelected]);
    setCheckedEmployeeIds(new Set());
    setNotes('');
  };

  // Remove a single employee from selected list (optionally by meal type)
  const removeSelectedEmployee = (employeeId: number, mealType?: string) => {
    if (mealType) {
      setSelectedEmployees(
        selectedEmployees.filter(
          (emp) => !(emp.id === employeeId && emp.mealType === mealType)
        )
      );
    } else {
      setSelectedEmployees(selectedEmployees.filter((emp) => emp.id !== employeeId));
    }
  };

  // Remove all selected employees
  const removeAllSelectedEmployees = () => {
    setSelectedEmployees([]);
  };

  return (
    <MealRequestContext.Provider
      value={{
        mealTypes,
        selectedDepartments,
        setSelectedDepartments,
        selectedEmployees,
        setSelectedEmployees,
        checkedEmployeeIds,
        setCheckedEmployeeIds,
        selectedMealTypes,
        toggleMealType,
        notes,
        setNotes,
        addSelectedEmployees,
        removeSelectedEmployee,
        removeAllSelectedEmployees,
      }}
    >
      {children}
    </MealRequestContext.Provider>
  );
}

export function useMealRequest() {
  const context = useContext(MealRequestContext);
  if (!context) {
    throw new Error('useMealRequest must be used within MealRequestProvider');
  }
  return context;
}
