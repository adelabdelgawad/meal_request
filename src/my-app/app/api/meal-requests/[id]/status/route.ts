/**
 * API Route: /api/meal-requests/[id]/status
 * Handles meal request status updates (approve/reject)
 */

import { NextRequest, NextResponse } from 'next/server';
import { serverApi } from '@/lib/http/axios-server';

interface RouteParams {
  params: Promise<{ id: string }>;
}

/**
 * PUT /api/meal-requests/[id]/status
 * Update meal request status (approve or reject)
 */
export async function PUT(request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params;

    // Extract query parameters
    const { searchParams } = request.nextUrl;
    const statusId = searchParams.get('status_id');
    const userId = searchParams.get('user_id');

    if (!statusId || !userId) {
      return NextResponse.json(
        {
          ok: false,
          error: 'invalid_params',
          message: 'status_id and user_id are required',
        },
        { status: 400 }
      );
    }

    // Call backend API
    const result = await serverApi.put(
      `/requests/${id}/status`,
      {},
      {
        params: {
          status_id: statusId,
          user_id: userId,
        },
        useVersioning: true, // /api/v1/requests/{id}/status
      }
    );

    if (!result.ok) {
      return NextResponse.json(
        {
          ok: false,
          error: result.error,
          message: result.message,
        },
        { status: result.status }
      );
    }

    return NextResponse.json(
      {
        ok: true,
        data: result.data,
      },
      { status: 200 }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error('PUT /api/meal-requests/[id]/status error:', errorMessage);

    return NextResponse.json(
      {
        ok: false,
        error: 'server_error',
        message: 'Failed to update meal request status',
      },
      { status: 500 }
    );
  }
}
