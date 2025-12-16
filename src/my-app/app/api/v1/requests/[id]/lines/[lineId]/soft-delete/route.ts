import { NextRequest, NextResponse } from 'next/server';
import { serverApi } from '@/lib/http/axios-server';

/**
 * DELETE /api/v1/requests/[id]/lines/[lineId]/soft-delete
 * Soft delete a meal request line (removes employee from request)
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string; lineId: string }> }
) {
  try {
    const { id, lineId } = await params;

    // Forward the delete request to the backend
    const result = await serverApi.delete(`/api/v1/requests/${id}/lines/${lineId}/soft-delete`);

    if (!result.ok) {
      return NextResponse.json(
        { error: result.error || 'Failed to delete request line' },
        { status: result.status || 500 }
      );
    }

    return NextResponse.json(result.data, { status: 200 });
  } catch (error) {
    console.error('Error deleting meal request line:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
