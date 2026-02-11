// app/(pages)/setting/users/page.tsx
import { getRoles } from "@/lib/actions/roles.actions";
import { getDomainUsers, getUsers } from "@/lib/actions/users.actions";
import { getAllDepartments } from "@/lib/actions/departments.actions";
import UsersTable from "./_components/table/users-table";
import type { AuthUserResponse } from "@/types/users";

export default async function UsersPage({
  searchParams,
}: {
  searchParams: Promise<{
    is_active?: string;
    search?: string;
    page?: string;
    limit?: string;
    role?: string;
    user_source?: string;
    status_override?: string;
  }>;
}) {
  // Await searchParams before destructuring
  const params = await searchParams;
  const { is_active, search, page, limit, role, user_source, status_override } = params;

  const pageNumber = Number(page) || 1;
  const limitNumber = Number(limit) || 10;
  const skip = (pageNumber - 1) * limitNumber;

  // Create a filters object to pass to getUsers (using snake_case for URL params)
  const filters = {
    is_active: is_active,
    username: search,
    role: role,
    user_source: user_source,
    status_override: status_override,
  };

  const users = await getUsers(limitNumber, skip, filters);

  // Fetch ALL roles for the add/edit user forms (not paginated)
  const rolesResponse = await getRoles({
    limit: 1000, // Large limit to get all roles
    skip: 0,
    filterCriteria: {
      is_active: 'true' // Only active roles
    }
  });
  const roles = rolesResponse.roles ?? [];

  // Get domain users with fallback to empty array
  let domainUsers: AuthUserResponse[] = [];
  try {
    domainUsers = (await getDomainUsers()) ?? [];
  } catch {
    domainUsers = [];
  }

  // Get all departments for department assignment sheet (server-side loaded)
  const departments = await getAllDepartments();

  return (
    <UsersTable
      initialData={users}
      roles={roles}
      domainUsers={domainUsers}
      departments={departments}
    />
  );
}
