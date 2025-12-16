// app/(pages)/history-requests/page.tsx
import { getMyMealRequests, getMealRequestStatusOptions } from '@/lib/actions/requests.actions';
import { HistoryDataTable } from './_components/history-data-table';

export default async function HistoryRequestsPage({
  searchParams,
}: {
  searchParams: Promise<{
    status?: string;
    from_date?: string;
    to_date?: string;
    page?: string;
    limit?: string;
  }>;
}) {
  // Await searchParams before destructuring
  const params = await searchParams;
  const { status, from_date, to_date, page, limit } = params;

  const currentPage = page ? parseInt(page, 10) : 1;
  const pageSize = limit ? parseInt(limit, 10) : 10;

  // Create filters object - only include date filters if explicitly provided
  const filters = {
    status,
    from_date,
    to_date,
    page: currentPage,
    page_size: pageSize,
  };

  // Fetch user's own meal requests and status options on the server
  const [initialData, statusOptions] = await Promise.all([
    getMyMealRequests(filters),
    getMealRequestStatusOptions(true), // Fetch only active statuses
  ]);

  // Use stats from the unified response
  const initialStats = initialData.stats;

  return (
    <div className="flex flex-col min-h-screen p-4 md:p-6 bg-background">
      <HistoryDataTable
        initialData={initialData}
        initialStats={initialStats}
        statusOptions={statusOptions}
      />
    </div>
  );
}
