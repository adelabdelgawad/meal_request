"use client"

import * as React from "react"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"
import { CalendarIcon } from "lucide-react"
import { format, subDays, startOfDay, endOfDay, startOfWeek, endOfWeek, startOfMonth, endOfMonth } from "date-fns"
import { ar, enUS } from "date-fns/locale"
import { useLanguage } from "@/hooks/use-language"

export interface DateRange {
  from: Date | undefined
  to: Date | undefined
}

interface DateTimeRangePickerProps {
  /**
   * The selected date range
   */
  dateRange?: DateRange
  /**
   * Callback when date range changes
   */
  onDateRangeChange?: (range: DateRange | undefined) => void
  /**
   * Callback when Apply button is clicked
   * If provided, date changes are buffered and only applied on click
   */
  onApply?: (range: DateRange | undefined) => void
  /**
   * Placeholder text when no range is selected
   */
  placeholder?: string
  /**
   * Disabled state
   */
  disabled?: boolean
  /**
   * Custom className for the trigger button
   */
  className?: string
  /**
   * Show preset buttons
   */
  showPresets?: boolean
  /**
   * Custom preset configurations
   */
  presets?: DateRangePreset[]
  /**
   * Translation function for labels
   */
  t?: (key: string) => string
}

export interface DateRangePreset {
  label: string
  getValue: () => DateRange
}

/**
 * Get default presets for date range selection
 */
export const getDefaultPresets = (t?: (key: string) => string): DateRangePreset[] => {
  const translate = t || ((key: string) => key)

  return [
    {
      label: translate("datePicker.presets.today"),
      getValue: () => ({
        from: startOfDay(new Date()),
        to: endOfDay(new Date()),
      }),
    },
    {
      label: translate("datePicker.presets.yesterday"),
      getValue: () => {
        const yesterday = subDays(new Date(), 1)
        return {
          from: startOfDay(yesterday),
          to: endOfDay(yesterday),
        }
      },
    },
    {
      label: translate("datePicker.presets.last7Days"),
      getValue: () => ({
        from: startOfDay(subDays(new Date(), 6)),
        to: endOfDay(new Date()),
      }),
    },
    {
      label: translate("datePicker.presets.last30Days"),
      getValue: () => ({
        from: startOfDay(subDays(new Date(), 29)),
        to: endOfDay(new Date()),
      }),
    },
    {
      label: translate("datePicker.presets.thisWeek"),
      getValue: () => ({
        from: startOfWeek(new Date(), { weekStartsOn: 0 }),
        to: endOfWeek(new Date(), { weekStartsOn: 0 }),
      }),
    },
    {
      label: translate("datePicker.presets.thisMonth"),
      getValue: () => ({
        from: startOfMonth(new Date()),
        to: endOfMonth(new Date()),
      }),
    },
  ]
}

/**
 * DateTimeRangePicker component for selecting a date/time range
 *
 * Features:
 * - Calendar with range selection
 * - Time inputs for start and end times (HH:mm precision)
 * - Preset buttons for common ranges (Today, Yesterday, Last 7 days, etc.)
 * - Single button trigger with formatted range display
 * - i18n support
 * - Validation (end time >= start time)
 */
export function DateTimeRangePicker({
  dateRange,
  onDateRangeChange,
  onApply,
  placeholder = "Pick a date range",
  disabled = false,
  className,
  showPresets = true,
  presets,
  t,
}: DateTimeRangePickerProps) {
  const [isOpen, setIsOpen] = React.useState(false)
  const [selectedPresetIndex, setSelectedPresetIndex] = React.useState<number | null>(null)

  // Get current language for locale-aware date formatting
  const { language } = useLanguage()
  const dateLocale = language === 'ar' ? ar : enUS

  // Local state for time inputs
  const [startTime, setStartTime] = React.useState(() => {
    if (!dateRange?.from) return "00:00"
    const hours = dateRange.from.getHours().toString().padStart(2, '0')
    const minutes = dateRange.from.getMinutes().toString().padStart(2, '0')
    return `${hours}:${minutes}`
  })

  const [endTime, setEndTime] = React.useState(() => {
    if (!dateRange?.to) return "23:59"
    const hours = dateRange.to.getHours().toString().padStart(2, '0')
    const minutes = dateRange.to.getMinutes().toString().padStart(2, '0')
    return `${hours}:${minutes}`
  })

  // Update time values when dateRange changes externally
  React.useEffect(() => {
    if (dateRange?.from) {
      const hours = dateRange.from.getHours().toString().padStart(2, '0')
      const minutes = dateRange.from.getMinutes().toString().padStart(2, '0')
      setStartTime(`${hours}:${minutes}`)
    }
  }, [dateRange?.from])

  React.useEffect(() => {
    if (dateRange?.to) {
      const hours = dateRange.to.getHours().toString().padStart(2, '0')
      const minutes = dateRange.to.getMinutes().toString().padStart(2, '0')
      setEndTime(`${hours}:${minutes}`)
    }
  }, [dateRange?.to])

  /**
   * Handle calendar range selection
   */
  const handleRangeSelect = (range: { from?: Date; to?: Date } | undefined) => {
    // Clear preset selection when user manually picks dates
    setSelectedPresetIndex(null)

    if (!range) {
      onDateRangeChange?.(undefined)
      return
    }

    // Parse time values
    const [startHours, startMinutes] = startTime.split(':').map(Number)
    const [endHours, endMinutes] = endTime.split(':').map(Number)

    // Create new dates with selected dates and current times
    const fromDate = range.from ? new Date(range.from) : undefined
    const toDate = range.to ? new Date(range.to) : undefined

    if (fromDate) {
      fromDate.setHours(startHours || 0, startMinutes || 0, 0, 0)
    }

    if (toDate) {
      toDate.setHours(endHours || 23, endMinutes || 59, 0, 0)
    }

    onDateRangeChange?.({
      from: fromDate,
      to: toDate,
    })
  }

  /**
   * Handle start time change
   */
  const handleStartTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setStartTime(value)

    // Clear preset selection when user manually changes time
    setSelectedPresetIndex(null)

    // Only update if we have a valid time format
    if (!/^\d{2}:\d{2}$/.test(value)) return

    const [hours, minutes] = value.split(':').map(Number)
    if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59) return

    if (dateRange?.from) {
      const newFrom = new Date(dateRange.from)
      newFrom.setHours(hours, minutes, 0, 0)

      onDateRangeChange?.({
        from: newFrom,
        to: dateRange.to,
      })
    }
  }

  /**
   * Handle end time change
   */
  const handleEndTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setEndTime(value)

    // Clear preset selection when user manually changes time
    setSelectedPresetIndex(null)

    // Only update if we have a valid time format
    if (!/^\d{2}:\d{2}$/.test(value)) return

    const [hours, minutes] = value.split(':').map(Number)
    if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59) return

    if (dateRange?.to) {
      const newTo = new Date(dateRange.to)
      newTo.setHours(hours, minutes, 0, 0)

      onDateRangeChange?.({
        from: dateRange.from,
        to: newTo,
      })
    }
  }

  /**
   * Handle preset selection
   */
  const handlePresetSelect = (preset: DateRangePreset, index: number) => {
    const range = preset.getValue()

    // Set active preset
    setSelectedPresetIndex(index)

    // Update local time state
    if (range.from) {
      const hours = range.from.getHours().toString().padStart(2, '0')
      const minutes = range.from.getMinutes().toString().padStart(2, '0')
      setStartTime(`${hours}:${minutes}`)
    }

    if (range.to) {
      const hours = range.to.getHours().toString().padStart(2, '0')
      const minutes = range.to.getMinutes().toString().padStart(2, '0')
      setEndTime(`${hours}:${minutes}`)
    }

    onDateRangeChange?.(range)
  }

  /**
   * Clear the selected range
   */
  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation()
    setSelectedPresetIndex(null)
    onDateRangeChange?.(undefined)
    // If onApply is provided, also call it to immediately clear filters
    if (onApply) {
      onApply(undefined)
    }
    setStartTime("00:00")
    setEndTime("23:59")
  }

  /**
   * Format the displayed date range with locale awareness
   * Uses date-fns locale for proper Arabic/English formatting
   */
  const formatDisplayRange = () => {
    if (!dateRange?.from) {
      return placeholder
    }

    try {
      // Use locale-aware format pattern
      // For Arabic: Use explicit pattern to ensure Arabic AM/PM (ص/م)
      // For English: Use PPp (Medium date + short time)
      const formatPattern = language === 'ar'
        ? "d MMMM yyyy، h:mm a"  // Arabic: ١٥ ديسمبر ٢٠٢٥، ٢:٣٠ م
        : "PPp"                   // English: Dec 15, 2025, 2:30 PM

      if (!dateRange.to) {
        return format(dateRange.from, formatPattern, { locale: dateLocale })
      }

      return `${format(dateRange.from, formatPattern, { locale: dateLocale })} - ${format(dateRange.to, formatPattern, { locale: dateLocale })}`
    } catch (error) {
      console.error("Error formatting date range:", error)
      return placeholder
    }
  }

  const presetsToUse = presets || getDefaultPresets(t)

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            "justify-start text-left font-normal",
            !dateRange?.from && "text-muted-foreground",
            className
          )}
          disabled={disabled}
        >
          <CalendarIcon className="mr-2" />
          <span className="truncate">{formatDisplayRange()}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <div className="flex flex-col">
          {/* Top Row: Presets and Calendar */}
          <div className="flex flex-col md:flex-row">
            {/* Left: Presets */}
            {showPresets && (
              <div className="p-3 space-y-1.5 md:border-r border-border/50 bg-muted/30 w-full md:w-[150px]">
                <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                  {t?.("datePicker.presets.title") || "Presets"}
                </div>
                {presetsToUse.map((preset, index) => (
                  <Button
                    key={index}
                    variant={selectedPresetIndex === index ? "secondary" : "ghost"}
                    size="sm"
                    className={cn(
                      "w-full justify-start font-normal text-sm transition-all",
                      selectedPresetIndex === index && "bg-secondary/80 shadow-sm font-medium"
                    )}
                    onClick={() => handlePresetSelect(preset, index)}
                  >
                    {preset.label}
                  </Button>
                ))}
              </div>
            )}

            {/* Right: Calendar */}
            <div className="p-2">
              <Calendar
                mode="range"
                selected={{ from: dateRange?.from, to: dateRange?.to }}
                onSelect={handleRangeSelect}
                numberOfMonths={1}
                initialFocus
              />
            </div>
          </div>

          <Separator />

          {/* Bottom: Time Range - Full Width */}
          <div className="p-3 space-y-3 bg-muted/20">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              {t?.("datePicker.timeRange") || "Time Range"}
            </div>

            {/* Start and End Time on Same Row */}
            <div className="flex items-center gap-3">
              {/* Start Time */}
              <div className="flex items-center gap-2 flex-1">
                <label htmlFor="start-time" className="text-xs font-medium text-muted-foreground whitespace-nowrap min-w-[36px]">
                  {t?.("datePicker.from") || "From"}
                </label>
                <Input
                  id="start-time"
                  type="time"
                  value={startTime}
                  onChange={handleStartTimeChange}
                  className="h-8 text-sm flex-1"
                  step="60"
                />
              </div>

              {/* End Time */}
              <div className="flex items-center gap-2 flex-1">
                <label htmlFor="end-time" className="text-xs font-medium text-muted-foreground whitespace-nowrap min-w-[24px]">
                  {t?.("datePicker.to") || "To"}
                </label>
                <Input
                  id="end-time"
                  type="time"
                  value={endTime}
                  onChange={handleEndTimeChange}
                  className="h-8 text-sm flex-1"
                  step="60"
                />
              </div>
            </div>
          </div>

          <Separator />

          {/* Bottom: Action Buttons - Full Width */}
          <div className="flex gap-2 p-3 bg-background">
            <Button
              size="sm"
              variant="outline"
              className="flex-1"
              onClick={handleClear}
            >
              {t?.("datePicker.clear") || "Clear"}
            </Button>
            <Button
              size="sm"
              className="flex-1"
              onClick={() => {
                if (onApply) {
                  onApply(dateRange);
                }
                setIsOpen(false);
              }}
            >
              {t?.("datePicker.apply") || "Apply"}
            </Button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}
