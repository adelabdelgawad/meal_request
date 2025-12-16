'use client';

import { CalendarIcon, ChevronLeft, ChevronRight, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useState } from 'react';
import { LiveIndicator } from '@/app/(pages)/requests/_components/live-indicator';
import { useLanguage } from '@/hooks/use-language';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  format,
  startOfMonth,
  endOfMonth,
  eachDayOfInterval,
  addMonths,
  subMonths,
  isSameMonth,
  isSameDay,
  startOfWeek,
  endOfWeek,
} from 'date-fns';
import { ar, enUS, type Locale } from 'date-fns/locale';

interface AnalysisFiltersProps {
  fromDate: string;
  toDate: string;
  isLive: boolean;
  isValidating?: boolean;
  onFromDateChange: (value: string) => void;
  onToDateChange: (value: string) => void;
}

// Single Date Picker Component
function SingleDatePicker({
  value,
  onChange,
  placeholder,
  dateLocale,
  isRtl,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  dateLocale: Locale;
  isRtl: boolean;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [currentMonth, setCurrentMonth] = useState(() =>
    value ? new Date(value) : new Date()
  );

  // Handle popover open/close with month reset
  const handleOpenChange = (newIsOpen: boolean) => {
    if (newIsOpen) {
      // Reset to selected date's month when opening
      setCurrentMonth(value ? new Date(value) : new Date());
    }
    setIsOpen(newIsOpen);
  };

  const selectedDate = value ? new Date(value) : undefined;

  // Navigate months
  const goToPreviousMonth = () => setCurrentMonth(subMonths(currentMonth, 1));
  const goToNextMonth = () => setCurrentMonth(addMonths(currentMonth, 1));

  // Generate calendar days
  const getDaysInMonth = () => {
    const monthStart = startOfMonth(currentMonth);
    const monthEnd = endOfMonth(currentMonth);
    const calendarStart = startOfWeek(monthStart, { weekStartsOn: 0 });
    const calendarEnd = endOfWeek(monthEnd, { weekStartsOn: 0 });
    return eachDayOfInterval({ start: calendarStart, end: calendarEnd });
  };

  // Handle day click
  const handleDayClick = (day: Date) => {
    const dateTime = new Date(day);
    dateTime.setHours(0, 0, 0, 0);
    onChange(dateTime.toISOString());
    setIsOpen(false);
  };

  // Clear date
  const clearDate = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange('');
  };

  // Weekday headers
  const weekdays = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];

  return (
    <Popover open={isOpen} onOpenChange={handleOpenChange}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={`h-9 min-w-[140px] justify-start text-left font-normal gap-2 ${!selectedDate && 'text-muted-foreground'}`}
        >
          <CalendarIcon className="h-4 w-4 shrink-0" />
          <span className="truncate">
            {selectedDate ? format(selectedDate, 'M/d/yyyy') : placeholder}
          </span>
          {selectedDate && (
            <X
              className="h-4 w-4 ms-auto shrink-0 opacity-50 hover:opacity-100"
              onClick={clearDate}
            />
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-3" align={isRtl ? 'start' : 'end'}>
        {/* Month Navigation Header */}
        <div className="flex items-center justify-between mb-3">
          <button
            type="button"
            onClick={goToPreviousMonth}
            className="p-1 hover:bg-accent rounded transition-colors"
          >
            <ChevronLeft className="h-5 w-5 text-muted-foreground" />
          </button>
          <span className="font-medium text-foreground">
            {format(currentMonth, 'MMMM yyyy', { locale: dateLocale })}
          </span>
          <button
            type="button"
            onClick={goToNextMonth}
            className="p-1 hover:bg-accent rounded transition-colors"
          >
            <ChevronRight className="h-5 w-5 text-muted-foreground" />
          </button>
        </div>

        {/* Weekday Headers */}
        <div className="grid grid-cols-7 gap-0 mb-1">
          {weekdays.map((day) => (
            <div
              key={day}
              className="h-8 flex items-center justify-center text-sm text-muted-foreground font-normal"
            >
              {day}
            </div>
          ))}
        </div>

        {/* Calendar Days */}
        <div className="grid grid-cols-7 gap-0">
          {getDaysInMonth().map((day, index) => {
            const isCurrentMonth = isSameMonth(day, currentMonth);
            const isSelected = selectedDate && isSameDay(day, selectedDate);
            const isToday = isSameDay(day, new Date());

            return (
              <button
                key={index}
                type="button"
                onClick={() => handleDayClick(day)}
                className={`
                  h-8 w-8 flex items-center justify-center text-sm rounded-md transition-colors
                  ${!isCurrentMonth ? 'text-muted-foreground/40' : 'text-foreground'}
                  ${isSelected ? 'bg-primary text-primary-foreground font-medium' : ''}
                  ${!isSelected && isCurrentMonth ? 'hover:bg-accent' : ''}
                  ${isToday && !isSelected ? 'ring-1 ring-primary' : ''}
                `}
              >
                {format(day, 'd')}
              </button>
            );
          })}
        </div>
      </PopoverContent>
    </Popover>
  );
}

export function AnalysisFilters({
  fromDate,
  toDate,
  isLive,
  isValidating = false,
  onFromDateChange,
  onToDateChange,
}: AnalysisFiltersProps) {
  const { t, language } = useLanguage();
  const isRtl = language === 'ar';
  const dateLocale = language === 'ar' ? ar : enUS;

  // Get translations
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const filters = ((t?.analysis as Record<string, unknown>)?.filters || {}) as any;

  const hasFilters = fromDate || toDate;

  const clearAllFilters = () => {
    onFromDateChange('');
    onToDateChange('');
  };

  return (
    <div className="bg-card rounded-lg border shadow-sm p-4">
      <div className={`flex flex-col sm:flex-row items-stretch sm:items-center gap-3 ${isRtl ? 'sm:flex-row-reverse' : ''}`}>
        {/* From Date Picker */}
        <div className="flex items-center gap-1">
          <span className="text-sm text-muted-foreground whitespace-nowrap">
            {filters.from || 'From'}:
          </span>
          <SingleDatePicker
            value={fromDate}
            onChange={onFromDateChange}
            placeholder={filters.selectDate || 'Select date'}
            dateLocale={dateLocale}
            isRtl={isRtl}
          />
        </div>

        {/* To Date Picker */}
        <div className="flex items-center gap-1">
          <span className="text-sm text-muted-foreground whitespace-nowrap">
            {filters.to || 'To'}:
          </span>
          <SingleDatePicker
            value={toDate}
            onChange={onToDateChange}
            placeholder={filters.selectDate || 'Select date'}
            dateLocale={dateLocale}
            isRtl={isRtl}
          />
        </div>

        {/* Status and Actions */}
        <div className={`flex items-center gap-2 ms-auto ${isRtl ? 'flex-row-reverse' : ''}`}>
          <LiveIndicator isLive={isLive} isValidating={isValidating} />
          {hasFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAllFilters}
              className="h-9 text-xs text-muted-foreground hover:text-foreground"
            >
              <X className="h-3 w-3 me-1" />
              {filters.clearAll || 'Clear all'}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
