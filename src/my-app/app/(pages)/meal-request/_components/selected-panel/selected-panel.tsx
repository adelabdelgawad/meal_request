'use client';

import { Button } from '@/components/ui/button';
import { ClipboardList, X, Trash2, Sun, Moon, StickyNote, Utensils } from 'lucide-react';
import { useMealRequest } from '../../context/meal-request-context';
import { useLanguage, translate } from '@/hooks/use-language';
import { getLocalizedName, getMealTypeName } from '@/types/meal-request.types';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

export function SelectedPanel() {
  const { mealTypes, selectedEmployees, removeSelectedEmployee, removeAllSelectedEmployees } =
    useMealRequest();
  const { language, t } = useLanguage();

  // Helper to get meal type by ID
  const getMealTypeById = (id: string) => {
    return mealTypes.find((mt) => mt.id.toString() === id);
  };

  // Helper to determine icon and colors based on meal type name
  const getMealTypeStyle = (nameEn: string) => {
    const lowerName = nameEn.toLowerCase();

    if (lowerName.includes('lunch')) {
      return {
        icon: Sun,
        borderColor: 'border-amber-200 dark:border-amber-800',
        bgColor: 'bg-amber-50/50 dark:bg-amber-950/30',
        badgeBg: 'bg-amber-100 dark:bg-amber-900/50',
        badgeText: 'text-amber-700 dark:text-amber-300',
      };
    } else if (lowerName.includes('dinner')) {
      return {
        icon: Moon,
        borderColor: 'border-indigo-200 dark:border-indigo-800',
        bgColor: 'bg-indigo-50/50 dark:bg-indigo-950/30',
        badgeBg: 'bg-indigo-100 dark:bg-indigo-900/50',
        badgeText: 'text-indigo-700 dark:text-indigo-300',
      };
    } else {
      return {
        icon: Utensils,
        borderColor: 'border-green-200 dark:border-green-800',
        bgColor: 'bg-green-50/50 dark:bg-green-950/30',
        badgeBg: 'bg-green-100 dark:bg-green-900/50',
        badgeText: 'text-green-700 dark:text-green-300',
      };
    }
  };

  const handleRemoveAll = () => {
    removeAllSelectedEmployees();
    toast.success(translate(t, 'mealRequest.toast.allRemoved'));
  };

  const handleRemove = (employeeId: number, mealType: string) => {
    removeSelectedEmployee(employeeId, mealType);
    toast.success(translate(t, 'mealRequest.toast.employeeRemoved'));
  };

  // Count employees by meal type
  const mealTypeCounts = mealTypes.reduce((acc, mt) => {
    const id = mt.id.toString();
    acc[id] = {
      count: selectedEmployees.filter((e) => e.mealType === id).length,
      label: getMealTypeName(mt, language),
    };
    return acc;
  }, {} as Record<string, { count: number; label: string }>);

  // Create summary text for header
  const summaryText = Object.entries(mealTypeCounts)
    .filter(([, { count }]) => count > 0)
    .map(([, { count, label }]) => `${count}${label}`)
    .join('/');

  return (
    <div className="flex flex-col h-full">
      {/* Compact Header */}
      <div className="flex items-center gap-2 mb-2">
        <div className="p-1.5 rounded-md bg-violet-100 dark:bg-violet-900/50">
          <ClipboardList className="h-4 w-4 text-violet-600 dark:text-violet-400" />
        </div>
        <span className="text-sm font-medium">
          {selectedEmployees.length} {translate(t, 'mealRequest.departments.selected')}
          {selectedEmployees.length > 0 && summaryText && (
            <span className="text-muted-foreground font-normal ms-1">
              ({summaryText})
            </span>
          )}
        </span>
        {selectedEmployees.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRemoveAll}
            className="ms-auto h-7 px-2 text-xs text-destructive hover:text-destructive"
          >
            <Trash2 className="h-3 w-3 me-1" />
            {translate(t, 'mealRequest.selected.clear')}
          </Button>
        )}
      </div>

      <div className="flex-1 min-h-0 overflow-auto -mx-1 px-1">
        <div className="space-y-2 pe-1">
          {selectedEmployees.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="p-4 rounded-full bg-muted/50 mb-3">
                <ClipboardList className="h-10 w-10 text-muted-foreground/30" />
              </div>
              <p className="text-sm font-medium text-muted-foreground">{translate(t, 'mealRequest.selected.noSelection')}</p>
              <p className="text-xs text-muted-foreground/70 mt-1">
                {translate(t, 'mealRequest.selected.addFromLeft')}
              </p>
            </div>
          )}
          {selectedEmployees.map((emp) => {
            const mealType = getMealTypeById(emp.mealType);
            if (!mealType) return null;

            const style = getMealTypeStyle(mealType.nameEn);
            const Icon = style.icon;
            const mealTypeLabel = getMealTypeName(mealType, language);

            return (
              <div
                key={`${emp.id}-${emp.mealType}`}
                className={cn(
                  'relative p-3 rounded-lg border transition-all',
                  style.borderColor,
                  style.bgColor
                )}
              >
                <button
                  type="button"
                  onClick={() => handleRemove(emp.id, emp.mealType)}
                  className={cn(
                    'absolute top-2 end-2 p-1 rounded-md transition-colors',
                    'hover:bg-destructive/10 text-muted-foreground hover:text-destructive'
                  )}
                >
                  <X className="h-4 w-4" />
                </button>

                <div className="pe-6">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span
                      className={cn(
                        'text-xs font-mono px-1.5 py-0.5 rounded',
                        style.badgeBg,
                        style.badgeText
                      )}
                    >
                      {emp.code}
                    </span>
                    <div
                      className={cn(
                        'flex items-center gap-1 px-1.5 py-0.5 rounded text-xs',
                        style.badgeBg,
                        style.badgeText
                      )}
                    >
                      <Icon className="h-3 w-3" />
                      {mealTypeLabel}
                    </div>
                  </div>

                  <p className="text-sm font-medium text-foreground truncate">
                    {getLocalizedName(emp.nameEn, emp.nameAr, language)}
                  </p>
                  <p className="text-xs text-muted-foreground truncate mt-0.5">
                    {emp.title}
                  </p>

                  {emp.note && (
                    <div className="flex items-start gap-1.5 mt-2 pt-2 border-t border-dashed border-muted-foreground/20">
                      <StickyNote className="h-3 w-3 text-muted-foreground shrink-0 mt-0.5" />
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {emp.note}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
