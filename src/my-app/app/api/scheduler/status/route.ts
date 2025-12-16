import { NextResponse } from "next/server";
import { serverApi } from "@/lib/http/axios-server";
import type { SchedulerStatusResponse } from "@/types/scheduler";

/**
 * GET /api/scheduler/status - Get scheduler status
 */
export async function GET() {
  try {
    const result = await serverApi.get<SchedulerStatusResponse>("/scheduler/status", {
      useVersioning: true,
    });

    if (!result.ok) {
      return NextResponse.json(
        { ok: false, error: result.error || "unknown_error", message: "Failed to fetch status" },
        { status: result.status || 500 }
      );
    }

    return NextResponse.json({ ok: true, data: result.data });
  } catch (error) {
    console.error("Error fetching scheduler status:", error);
    return NextResponse.json(
      { ok: false, error: "server_error", message: "Internal server error" },
      { status: 500 }
    );
  }
}
