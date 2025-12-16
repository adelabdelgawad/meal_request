import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";
import type { JobActionResponse } from "@/types/scheduler";

/**
 * POST /api/scheduler/jobs/[id]/action - Perform an action on a job
 * Actions: enable, disable, trigger, pause, resume
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await request.json();

    const result = await serverApi.post<JobActionResponse>(
      `/scheduler/jobs/${id}/action`,
      body,
      { useVersioning: true }
    );

    if (!result.ok) {
      return NextResponse.json(
        {
          ok: false,
          error: result.error || "unknown_error",
          message: result.message || "Failed to perform action"
        },
        { status: result.status || 500 }
      );
    }

    return NextResponse.json({ ok: true, data: result.data });
  } catch (error) {
    console.error("Error performing job action:", error);
    return NextResponse.json(
      { ok: false, error: "server_error", message: "Internal server error" },
      { status: 500 }
    );
  }
}
