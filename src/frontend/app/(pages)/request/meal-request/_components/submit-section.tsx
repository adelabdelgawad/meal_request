'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Loader2, Send, UtensilsCrossed } from 'lucide-react';
import { useMealRequest } from '../context/meal-request-context';
import { useSession } from '@/lib/auth/use-session';
import { useLanguage, translate } from '@/hooks/use-language';
import { createMealRequest } from '@/lib/actions/meal-requests.actions';
import { toast } from 'sonner';
import type { MealRequestLine } from '@/types/meal-request.types';
import { cn } from '@/lib/utils';

export function SubmitSection() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { mealTypes, selectedEmployees, setSelectedEmployees } = useMealRequest();
  const { user } = useSession();
  const { language, t } = useLanguage();

  // Count employees by meal type dynamically
  const mealTypeCounts = mealTypes.reduce((acc, mt) => {
    const id = mt.id.toString();
    const count = selectedEmployees.filter((e) => e.mealType === id).length;
    if (count > 0) {
      const label = language === 'ar' ? mt.nameAr : mt.nameEn;
      acc.push({ count, label });
    }
    return acc;
  }, [] as Array<{ count: number; label: string }>);

  // Generate summary text
  const summaryText = mealTypeCounts.map((m) => `${m.count}${m.label}`).join('/');

  const handleSubmit = async () => {
    if (!user?.id) {
      toast.error(translate(t, 'mealRequest.toast.error'));
      return;
    }

    if (selectedEmployees.length === 0) {
      toast.error(translate(t, 'mealRequest.submit.selectEmployees'));
      return;
    }

    setIsSubmitting(true);

    try {
      // Group employees by meal type
      const employeesByMealType = selectedEmployees.reduce(
        (acc, emp) => {
          if (!acc[emp.mealType]) {
            acc[emp.mealType] = [];
          }
          acc[emp.mealType].push({
            employeeId: emp.id,
            employeeCode: emp.code,
            notes: emp.note || '',
          });
          return acc;
        },
        {} as Record<string, MealRequestLine[]>
      );

      // Submit a request for each meal type
      const results = await Promise.all(
        Object.entries(employeesByMealType).map(([mealTypeId, requestLines]) =>
          createMealRequest(user.id, Number(mealTypeId), requestLines)
        )
      );

      // Check if any requests failed
      const failedRequests = results.filter((r) => !r.success);

      if (failedRequests.length > 0) {
        toast.error(translate(t, 'mealRequest.toast.error'));
      } else {
        toast.success(translate(t, 'mealRequest.toast.success'));
        setSelectedEmployees([]);
      }
    } catch (error) {
      console.error('Error submitting meal requests:', error);
      toast.error(translate(t, 'mealRequest.toast.error'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const hasSelection = selectedEmployees.length > 0;

  return (
    <div
      className={cn(
        'w-full px-4 py-2.5 rounded-lg border transition-all duration-300',
        hasSelection
          ? 'bg-primary/5 border-primary/20'
          : 'bg-muted/30 border-transparent'
      )}
    >
      <div className="flex items-center justify-between gap-4">
        {/* Summary */}
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'p-2 rounded-lg transition-colors',
              hasSelection ? 'bg-primary/10' : 'bg-muted'
            )}
          >
            <UtensilsCrossed
              className={cn(
                'h-5 w-5 transition-colors',
                hasSelection ? 'text-primary' : 'text-muted-foreground'
              )}
            />
          </div>
          <div>
            <p className="text-sm font-medium">
              {hasSelection ? (
                <>
                  <span className="text-primary">{selectedEmployees.length}</span>{' '}
                  {translate(t, 'mealRequest.submit.mealsReady').replace('{count}', '')}
                  {summaryText && (
                    <span className="text-muted-foreground font-normal ms-1.5 text-xs">
                      ({summaryText})
                    </span>
                  )}
                </>
              ) : (
                <span className="text-muted-foreground">{translate(t, 'mealRequest.submit.selectToSubmit')}</span>
              )}
            </p>
          </div>
        </div>

        {/* Submit Button */}
        <Button
          onClick={handleSubmit}
          disabled={!hasSelection || isSubmitting}
          className="gap-2"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              {translate(t, 'mealRequest.submit.submitting')}
            </>
          ) : (
            <>
              <Send className="h-4 w-4" />
              {translate(t, 'mealRequest.submit.button')}
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
