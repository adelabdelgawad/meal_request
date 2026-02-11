import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";
import type { SchedulerJobsResponse } from "@/types/scheduler";

/**
 * GET /api/scheduler/jobs - List scheduled jobs
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const params: Record<string, string> = {};

    // Forward pagination params
    const page = searchParams.get("page");
    const perPage = searchParams.get("per_page") || searchParams.get("limit");
    const skip = searchParams.get("skip");

    if (page) params.page = page;
    if (perPage) params.per_page = perPage;
    if (skip && perPage) {
      // Convert skip to page
      params.page = String(Math.floor(Number(skip) / Number(perPage)) + 1);
    }

    // Forward filter params
    const isEnabled = searchParams.get("is_enabled");
    const jobType = searchParams.get("job_type");

    if (isEnabled) params.is_enabled = isEnabled;
    if (jobType) params.job_type = jobType;

    const result = await serverApi.get<SchedulerJobsResponse>("/scheduler/jobs", {
      params,
      useVersioning: true,
    });

    if (!result.ok) {
      return NextResponse.json(
        { ok: false, error: result.error || "unknown_error", message: "Failed to fetch jobs" },
        { status: result.status || 500 }
      );
    }

    return NextResponse.json({ ok: true, data: result.data });
  } catch (error) {
    console.error("Error fetching scheduled jobs:", error);
    return NextResponse.json(
      { ok: false, error: "server_error", message: "Internal server error" },
      { status: 500 }
    );
  }
}

/**
 * POST /api/scheduler/jobs - Create a new job (interval or cron)
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const jobType = body.jobType || "interval";
    const endpoint = jobType === "cron" ? "/scheduler/jobs/cron" : "/scheduler/jobs/interval";

    const result = await serverApi.post(endpoint, body, {
      useVersioning: true,
    });

    if (!result.ok) {
      return NextResponse.json(
        { ok: false, error: result.error || "unknown_error", message: "Failed to create job" },
        { status: result.status || 500 }
      );
    }

    return NextResponse.json({ ok: true, data: result.data }, { status: 201 });
  } catch (error) {
    console.error("Error creating scheduled job:", error);
    return NextResponse.json(
      { ok: false, error: "server_error", message: "Internal server error" },
      { status: 500 }
    );
  }
}
