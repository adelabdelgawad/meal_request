'use client';

import { Sun, Moon, Check, Utensils } from 'lucide-react';
import { useMealRequest } from '../context/meal-request-context';
import { useLanguage } from '@/hooks/use-language';
import { getMealTypeName } from '@/types/meal-request.types';
import { cn } from '@/lib/utils';

export function MealTypeToggle() {
  const { mealTypes, selectedMealTypes, toggleMealType } = useMealRequest();
  const { language } = useLanguage();

  // Helper to determine icon and colors based on meal type name
  const getMealTypeStyle = (nameEn: string, index: number) => {
    const lowerName = nameEn.toLowerCase();

    if (lowerName.includes('lunch') || lowerName.includes('غداء')) {
      return {
        icon: Sun,
        activeBorder: 'border-amber-400 dark:border-amber-600',
        activeBg: 'bg-amber-50 dark:bg-amber-950/50',
        iconColor: 'text-amber-600 dark:text-amber-400',
        checkBg: 'bg-amber-500',
      };
    } else if (lowerName.includes('dinner') || lowerName.includes('عشاء')) {
      return {
        icon: Moon,
        activeBorder: 'border-indigo-400 dark:border-indigo-600',
        activeBg: 'bg-indigo-50 dark:bg-indigo-950/50',
        iconColor: 'text-indigo-600 dark:text-indigo-400',
        checkBg: 'bg-indigo-500',
      };
    } else {
      // Default styles for other meal types, use different colors by index
      const colors = [
        {
          activeBorder: 'border-green-400 dark:border-green-600',
          activeBg: 'bg-green-50 dark:bg-green-950/50',
          iconColor: 'text-green-600 dark:text-green-400',
          checkBg: 'bg-green-500',
        },
        {
          activeBorder: 'border-purple-400 dark:border-purple-600',
          activeBg: 'bg-purple-50 dark:bg-purple-950/50',
          iconColor: 'text-purple-600 dark:text-purple-400',
          checkBg: 'bg-purple-500',
        },
      ];
      return {
        icon: Utensils,
        ...colors[index % colors.length],
      };
    }
  };

  return (
    <div className="flex gap-1.5 flex-wrap">
      {mealTypes.map((mealType, index) => {
        const value = mealType.id.toString();
        const isActive = selectedMealTypes.has(value);
        const style = getMealTypeStyle(mealType.nameEn, index);
        const Icon = style.icon;
        const label = getMealTypeName(mealType, language);

        return (
          <button
            key={mealType.id}
            type="button"
            onClick={() => toggleMealType(value)}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all duration-200',
              'focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-primary/50',
              isActive
                ? cn('border', style.activeBorder, style.activeBg, 'shadow-sm')
                : 'border border-border bg-muted/30 text-muted-foreground hover:text-foreground hover:bg-muted/60'
            )}
          >
            <div
              className={cn(
                'flex items-center justify-center w-4 h-4 rounded border transition-colors',
                isActive
                  ? cn(style.checkBg, 'border-transparent')
                  : 'border-muted-foreground/40 bg-background'
              )}
            >
              {isActive && <Check className="h-3 w-3 text-white" />}
            </div>
            <Icon
              className={cn(
                'h-4 w-4 transition-colors',
                isActive ? style.iconColor : 'text-muted-foreground'
              )}
            />
            <span
              className={cn(
                'text-sm font-medium',
                isActive ? 'text-foreground' : 'text-muted-foreground'
              )}
            >
              {label}
            </span>
          </button>
        );
      })}
    </div>
  );
}
