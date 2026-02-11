import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";
import type { ScheduledJob } from "@/types/scheduler";

/**
 * GET /api/scheduler/jobs/[id] - Get a scheduled job by ID
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    const result = await serverApi.get<ScheduledJob>(`/scheduler/jobs/${id}`, {
      useVersioning: true,
    });

    if (!result.ok) {
      return NextResponse.json(
        { ok: false, error: result.error || "unknown_error", message: "Failed to fetch job" },
        { status: result.status || 500 }
      );
    }

    return NextResponse.json({ ok: true, data: result.data });
  } catch (error) {
    console.error("Error fetching scheduled job:", error);
    return NextResponse.json(
      { ok: false, error: "server_error", message: "Internal server error" },
      { status: 500 }
    );
  }
}

/**
 * PUT /api/scheduler/jobs/[id] - Update a scheduled job
 */
export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await request.json();

    const result = await serverApi.put<ScheduledJob>(`/scheduler/jobs/${id}`, body, {
      useVersioning: true,
    });

    if (!result.ok) {
      return NextResponse.json(
        { ok: false, error: result.error || "unknown_error", message: "Failed to update job" },
        { status: result.status || 500 }
      );
    }

    return NextResponse.json({ ok: true, data: result.data });
  } catch (error) {
    console.error("Error updating scheduled job:", error);
    return NextResponse.json(
      { ok: false, error: "server_error", message: "Internal server error" },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/scheduler/jobs/[id] - Delete a scheduled job
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    const result = await serverApi.delete(`/scheduler/jobs/${id}`, {
      useVersioning: true,
    });

    if (!result.ok) {
      return NextResponse.json(
        { ok: false, error: result.error || "unknown_error", message: "Failed to delete job" },
        { status: result.status || 500 }
      );
    }

    return NextResponse.json({ ok: true, data: result.data });
  } catch (error) {
    console.error("Error deleting scheduled job:", error);
    return NextResponse.json(
      { ok: false, error: "server_error", message: "Internal server error" },
      { status: 500 }
    );
  }
}
