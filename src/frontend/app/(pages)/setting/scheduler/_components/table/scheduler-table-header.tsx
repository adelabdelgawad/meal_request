"use client";

import { useMemo } from "react";
import { TableHeader, type ValueFormatter } from "@/components/data-table";
import type { ScheduledJob } from "@/types/scheduler";
import { useLanguage, translate } from "@/hooks/use-language";

interface SchedulerTableHeaderProps {
  page: number;
  tableInstance: import("@tanstack/react-table").Table<ScheduledJob> | null;
}

/**
 * Header section of the scheduler table with search and export controls
 */
export function SchedulerTableHeader({
  page,
  tableInstance,
}: SchedulerTableHeaderProps) {
  const { t, language } = useLanguage();

  // Value formatters for export
  const exportValueFormatters = useMemo<Record<string, ValueFormatter<ScheduledJob>>>(() => ({
    // Format isEnabled column
    isEnabled: (value: unknown) => {
      return value ? (translate(t, 'common.yes') || 'Yes') : (translate(t, 'common.no') || 'No');
    },
    // Format name based on language
    name: (_value: unknown, row: ScheduledJob) => {
      return (language === "ar" ? row.nameAr : row.nameEn) || "";
    },
    // Format description based on language
    description: (_value: unknown, row: ScheduledJob) => {
      return (language === "ar" ? row.descriptionAr : row.descriptionEn) || "";
    },
    // Format schedule
    schedule: (_value: unknown, row: ScheduledJob) => {
      if (row.jobType === "cron" && row.cronExpression) {
        return row.cronExpression;
      }
      const parts: string[] = [];
      if (row.intervalDays) parts.push(`${row.intervalDays}d`);
      if (row.intervalHours) parts.push(`${row.intervalHours}h`);
      if (row.intervalMinutes) parts.push(`${row.intervalMinutes}m`);
      if (row.intervalSeconds) parts.push(`${row.intervalSeconds}s`);
      return parts.length > 0 ? parts.join(" ") : "-";
    },
  }), [t, language]);

  // Header labels for export (translated)
  const exportHeaderLabels = useMemo(() => ({
    jobKey: translate(t, 'scheduler.columns.jobKey'),
    name: translate(t, 'scheduler.columns.name'),
    jobType: translate(t, 'scheduler.columns.type'),
    schedule: translate(t, 'scheduler.columns.schedule'),
    priority: translate(t, 'scheduler.columns.priority'),
    isEnabled: translate(t, 'scheduler.columns.enabled'),
    nextRunTime: translate(t, 'scheduler.columns.nextRun'),
    lastRunTime: translate(t, 'scheduler.columns.lastRun'),
    lastRunStatus: translate(t, 'scheduler.columns.status'),
  }), [t]);

  return (
    <TableHeader
      page={page}
      tableInstance={tableInstance}
      searchPlaceholder={translate(t, 'scheduler.search') || 'Search jobs...'}
      searchUrlParam="search"
      exportFilename={translate(t, 'scheduler.exportFilename') || 'scheduled-jobs'}
      printTitle={translate(t, 'scheduler.printTitle') || 'Scheduled Jobs'}
      exportValueFormatters={exportValueFormatters}
      exportHeaderLabels={exportHeaderLabels}
    />
  );
}
