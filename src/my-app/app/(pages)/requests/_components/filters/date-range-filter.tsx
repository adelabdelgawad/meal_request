'use client';

import { Calendar, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { format } from 'date-fns';

interface DateRangeFilterProps {
  fromDate: string;
  toDate: string;
  onFromDateChange: (value: string) => void;
  onToDateChange: (value: string) => void;
}

export function DateRangeFilter({
  fromDate,
  toDate,
  onFromDateChange,
  onToDateChange,
}: DateRangeFilterProps) {
  const formatDateForInput = (dateString: string) => {
    if (!dateString) return '';
    // Convert from ISO to datetime-local format
    return dateString.slice(0, 16);
  };

  const formatDisplayDate = (dateString: string) => {
    if (!dateString) return 'Select date';
    try {
      const date = new Date(dateString);
      return format(date, 'MMM dd, yyyy HH:mm');
    } catch {
      return 'Select date';
    }
  };

  const clearFromDate = () => onFromDateChange('');
  const clearToDate = () => onToDateChange('');

  return (
    <div className="flex flex-col md:flex-row gap-4">
      <div className="flex-1">
        <Label htmlFor="from-date" className="text-sm font-medium mb-1.5 block">
          From Date & Time
        </Label>
        <div className="relative">
          <Input
            id="from-date"
            type="datetime-local"
            value={formatDateForInput(fromDate)}
            onChange={(e) => onFromDateChange(e.target.value)}
            className="pr-20"
          />
          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
            {fromDate && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={clearFromDate}
                className="h-6 w-6 p-0 hover:bg-gray-200"
              >
                <X className="h-3 w-3" />
              </Button>
            )}
            <Calendar className="h-4 w-4 text-gray-400 pointer-events-none" />
          </div>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          {fromDate ? formatDisplayDate(fromDate) : 'No start date set'}
        </p>
      </div>

      <div className="flex-1">
        <Label htmlFor="to-date" className="text-sm font-medium mb-1.5 block">
          To Date & Time
        </Label>
        <div className="relative">
          <Input
            id="to-date"
            type="datetime-local"
            value={formatDateForInput(toDate)}
            onChange={(e) => onToDateChange(e.target.value)}
            className="pr-20"
          />
          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
            {toDate && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={clearToDate}
                className="h-6 w-6 p-0 hover:bg-gray-200"
              >
                <X className="h-3 w-3" />
              </Button>
            )}
            <Calendar className="h-4 w-4 text-gray-400 pointer-events-none" />
          </div>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          {toDate ? formatDisplayDate(toDate) : 'No end date set'}
        </p>
      </div>
    </div>
  );
}
