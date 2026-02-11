// app/(pages)/setting/roles/page.tsx
import { getAllUsers, getRoles } from "@/lib/actions/roles.actions";
import { getPages } from "@/lib/actions/pages.actions";
import RolesTable from "./_components/table/roles-table";
import type { PageResponse } from "@/types/pages";

export default async function RolesPage({
  searchParams,
}: {
  searchParams: Promise<{
    is_active?: string;
    page?: string;
    limit?: string;
    role_name?: string;
    role_id?: string;
  }>;
}) {
  const params = await searchParams;
  const { is_active, role_name, role_id, page: pageParam, limit: limitParam } = params;

  const page = Number(pageParam || "1");
  const limit = Number(limitParam || "10");
  const skip = (page - 1) * limit;

  const response = await getRoles({
    limit,
    skip,
    filterCriteria: {
      is_active: is_active || undefined,
      role_name: role_name || undefined,
      role_id: role_id || undefined,
    },
  });

  const [pagesResponse, users] = await Promise.all([
    getPages(),
    getAllUsers()
  ]);

  const pages: PageResponse[] = pagesResponse?.pages ?? [];

  return (
    <RolesTable
      initialData={response}
      preloadedPages={pages}
      preloadedUsers={users ?? []}
    />
  );
}
