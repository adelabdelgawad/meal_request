// app/(pages)/requests/page.tsx
import { getMealRequests, getMealRequestStatusOptions } from '@/lib/actions/requests.actions';
import { RequestsDataTable } from './_components/requests-data-table';

export default async function RequestsPage({
  searchParams,
}: {
  searchParams: Promise<{
    status?: string;
    requester?: string;
    from_date?: string;
    to_date?: string;
    page?: string;
    limit?: string;
  }>;
}) {
  // Await searchParams before destructuring
  const params = await searchParams;
  const { status, requester, from_date, to_date, page, limit } = params;

  const currentPage = page ? parseInt(page, 10) : 1;
  const pageSize = limit ? parseInt(limit, 10) : 10;

  // Create filters object - only include date filters if explicitly provided
  const filters = {
    status,
    requester,
    from_date,
    to_date,
    page: currentPage,
    page_size: pageSize,
  };

  // Fetch meal requests (with stats included) and status options on the server
  // Stats are now included in the unified response from getMealRequests
  const [initialData, statusOptions] = await Promise.all([
    getMealRequests(filters),
    getMealRequestStatusOptions(true), // Fetch only active statuses
  ]);

  // Use stats from the unified response
  const initialStats = initialData.stats;

  return (
    <div className="flex flex-col min-h-screen p-4 md:p-6 bg-background">
      <RequestsDataTable
        initialData={initialData}
        initialStats={initialStats}
        statusOptions={statusOptions}
      />
    </div>
  );
}
