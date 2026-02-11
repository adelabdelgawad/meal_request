"use client";

/**
 * SchedulerTableView - Pure UI component for displaying scheduler jobs
 *
 * This component only handles rendering. All data fetching and mutations
 * are handled by the parent SchedulerBody via useSchedulerJobs hook.
 * Actions are accessed via useSchedulerContext.
 */

import type { ScheduledJob } from "@/types/scheduler";
import SchedulerTableBody from "./scheduler-table-body";

interface SchedulerTableViewProps {
  jobs: ScheduledJob[];
  page: number;
}

function SchedulerTableView({ jobs, page }: SchedulerTableViewProps) {
  return <SchedulerTableBody jobs={jobs} page={page} />;
}

export default SchedulerTableView;
