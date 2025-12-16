// app/(pages)/scheduler/page.tsx
import {
  getScheduledJobs,
  getSchedulerStatus,
  getTaskFunctions,
  getJobTypes,
} from "@/lib/actions/scheduler.actions";
import { SchedulerBody } from "./_components/scheduler-body";

export default async function SchedulerPage({
  searchParams,
}: {
  searchParams: Promise<{
    is_enabled?: string;
    job_type?: string;
    page?: string;
    limit?: string;
  }>;
}) {
  // Await searchParams before destructuring
  const params = await searchParams;
  const { is_enabled, job_type, page, limit } = params;

  const pageNumber = Number(page) || 1;
  const limitNumber = Number(limit) || 10;
  const skip = (pageNumber - 1) * limitNumber;

  // Create a filters object
  const filters = {
    is_enabled: is_enabled,
    job_type: job_type,
  };

  // Fetch all data in parallel (jobs, status, and lookup data)
  const [jobs, status, taskFunctions, jobTypes] = await Promise.all([
    getScheduledJobs(limitNumber, skip, filters),
    getSchedulerStatus(),
    getTaskFunctions(),
    getJobTypes(),
  ]);
  console.table(jobs.items, [
    "id",
    "jobKey",
    "nameEn",
    "priority",
    "isEnabled",
    "nextRunTime",
  ]);
  return (
    <SchedulerBody
      initialData={jobs}
      initialStatus={status}
      taskFunctions={taskFunctions}
      jobTypes={jobTypes}
    />
  );
}
