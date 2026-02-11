"use client"

import * as React from "react"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { CalendarIcon } from "lucide-react"
import { format } from "date-fns"

interface DateTimePickerProps {
  /**
   * The selected date (can be Date or ISO string)
   */
  date?: Date | string
  /**
   * Callback when date/time changes
   */
  onDateChange?: (date: Date | undefined) => void
  /**
   * Placeholder text when no date is selected
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
   * Minimum selectable date
   */
  minDate?: Date
  /**
   * Maximum selectable date
   */
  maxDate?: Date
}

/**
 * DateTimePicker component that combines a calendar popover with time input
 *
 * Features:
 * - Calendar popover for date selection
 * - Time input with hour:minute precision (no seconds)
 * - Validates time input (00:00 - 23:59)
 * - Supports Date objects or ISO strings
 * - i18n ready (uses date-fns format)
 */
export function DateTimePicker({
  date: dateProp,
  onDateChange,
  placeholder = "Pick a date and time",
  disabled = false,
  className,
  minDate,
  maxDate,
}: DateTimePickerProps) {
  const [isOpen, setIsOpen] = React.useState(false)

  // Convert prop to Date object
  const selectedDate = React.useMemo(() => {
    if (!dateProp) return undefined
    return typeof dateProp === 'string' ? new Date(dateProp) : dateProp
  }, [dateProp])

  // Local state for time input (HH:mm format)
  const [timeValue, setTimeValue] = React.useState(() => {
    if (!selectedDate) return "00:00"
    const hours = selectedDate.getHours().toString().padStart(2, '0')
    const minutes = selectedDate.getMinutes().toString().padStart(2, '0')
    return `${hours}:${minutes}`
  })

  // Update time value when selected date changes externally
  React.useEffect(() => {
    if (selectedDate) {
      const hours = selectedDate.getHours().toString().padStart(2, '0')
      const minutes = selectedDate.getMinutes().toString().padStart(2, '0')
      setTimeValue(`${hours}:${minutes}`)
    }
  }, [selectedDate])

  /**
   * Handle calendar date selection
   */
  const handleDateSelect = (newDate: Date | undefined) => {
    if (!newDate) {
      onDateChange?.(undefined)
      return
    }

    // Parse current time value
    const [hours, minutes] = timeValue.split(':').map(Number)

    // Create new date with selected date and current time
    const dateWithTime = new Date(newDate)
    dateWithTime.setHours(hours || 0, minutes || 0, 0, 0)

    onDateChange?.(dateWithTime)
  }

  /**
   * Handle time input change
   */
  const handleTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setTimeValue(value)

    // Only update date if we have a valid time format (HH:mm)
    if (!/^\d{2}:\d{2}$/.test(value)) return

    const [hours, minutes] = value.split(':').map(Number)

    // Validate time range
    if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59) return

    if (selectedDate) {
      const newDate = new Date(selectedDate)
      newDate.setHours(hours, minutes, 0, 0)
      onDateChange?.(newDate)
    } else {
      // If no date selected, use today with the specified time
      const newDate = new Date()
      newDate.setHours(hours, minutes, 0, 0)
      onDateChange?.(newDate)
    }
  }

  /**
   * Clear the selected date/time
   */
  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation()
    onDateChange?.(undefined)
    setTimeValue("00:00")
  }

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            "justify-start text-left font-normal",
            !selectedDate && "text-muted-foreground",
            className
          )}
          disabled={disabled}
        >
          <CalendarIcon className="mr-2" />
          {selectedDate ? (
            <span>{format(selectedDate, "PPP HH:mm")}</span>
          ) : (
            <span>{placeholder}</span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <div className="flex flex-col">
          {/* Calendar */}
          <Calendar
            mode="single"
            selected={selectedDate}
            onSelect={handleDateSelect}
            disabled={(date) => {
              if (minDate && date < minDate) return true
              if (maxDate && date > maxDate) return true
              return false
            }}
            initialFocus
          />

          {/* Time Input */}
          <div className="border-t p-3 space-y-2">
            <div className="flex items-center gap-2">
              <label htmlFor="time-input" className="text-sm font-medium">
                Time:
              </label>
              <Input
                id="time-input"
                type="time"
                value={timeValue}
                onChange={handleTimeChange}
                className="w-auto"
                step="60"
              />
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                className="flex-1"
                onClick={handleClear}
              >
                Clear
              </Button>
              <Button
                size="sm"
                className="flex-1"
                onClick={() => setIsOpen(false)}
              >
                Done
              </Button>
            </div>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}
