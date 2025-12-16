'use client';

import { Building2, Users, UtensilsCrossed, ClipboardList } from 'lucide-react';
import { useMealRequest } from '../context/meal-request-context';
import { useLanguage, translate } from '@/hooks/use-language';
import { cn } from '@/lib/utils';

interface StatsHeaderProps {
  totalDepartments: number;
}

export function StatsHeader({ totalDepartments }: StatsHeaderProps) {
  const { mealTypes, selectedDepartments, selectedEmployees, checkedEmployeeIds } = useMealRequest();
  const { language, t } = useLanguage();

  // Count employees by meal type dynamically
  const mealTypeCounts = mealTypes.map((mt) => {
    const id = mt.id.toString();
    const count = selectedEmployees.filter((e) => e.mealType === id).length;
    const label = language === 'ar' ? mt.nameAr : mt.nameEn;
    return { count, label, short: translate(t, 'mealRequest.selected.lunch') }; // Short label placeholder
  });

  // Generate subtext for meal types stat
  const activeCounts = mealTypeCounts.filter((m) => m.count > 0);
  const mealTypeSubtext =
    activeCounts.length > 0
      ? activeCounts.map((m) => `${m.count} ${m.label}`).join(' / ')
      : translate(t, 'mealRequest.mealType.title');

  const stats = [
    {
      icon: Building2,
      value: selectedDepartments.length,
      subtext: `/ ${totalDepartments} ${translate(t, 'mealRequest.departments.depts')}`,
      color: 'text-blue-600 dark:text-blue-400',
      bgColor: 'bg-blue-50 dark:bg-blue-950/50',
      borderColor: 'border-blue-200 dark:border-blue-800',
    },
    {
      icon: Users,
      value: checkedEmployeeIds.size,
      subtext: translate(t, 'mealRequest.employees.checked'),
      color: 'text-amber-600 dark:text-amber-400',
      bgColor: 'bg-amber-50 dark:bg-amber-950/50',
      borderColor: 'border-amber-200 dark:border-amber-800',
    },
    {
      icon: ClipboardList,
      value: selectedEmployees.length,
      subtext: translate(t, 'mealRequest.departments.selected'),
      color: 'text-green-600 dark:text-green-400',
      bgColor: 'bg-green-50 dark:bg-green-950/50',
      borderColor: 'border-green-200 dark:border-green-800',
    },
    {
      icon: UtensilsCrossed,
      value: selectedEmployees.length,
      subtext: mealTypeSubtext,
      color: 'text-purple-600 dark:text-purple-400',
      bgColor: 'bg-purple-50 dark:bg-purple-950/50',
      borderColor: 'border-purple-200 dark:border-purple-800',
    },
  ];

  return (
    <div className="grid grid-cols-4 gap-1 mb-3">
      {stats.map((stat, idx) => (
        <div
          key={idx}
          className={cn(
            'flex items-center gap-2 px-4 py-2.5 rounded-lg border transition-all',
            stat.bgColor,
            stat.borderColor
          )}
        >
          <stat.icon className={cn('h-4 w-4 shrink-0', stat.color)} />
          <div className="flex items-baseline gap-1.5 min-w-0 flex-1">
            <span className={cn('text-lg font-bold leading-none', stat.color)}>
              {stat.value}
            </span>
            <span className="text-xs text-muted-foreground truncate">
              {stat.subtext}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
