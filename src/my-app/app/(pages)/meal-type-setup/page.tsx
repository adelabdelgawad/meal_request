import { getMealTypes } from "@/lib/actions/meal-types.actions";
import MealTypesTable from "./_components/table/meal-types-table";

export default async function MealTypeSetupPage({
  searchParams,
}: {
  searchParams: Promise<{
    active_only?: string;
    page?: string;
    limit?: string;
  }>;
}) {
  const params = await searchParams;
  const { active_only, page: pageParam, limit: limitParam } = params;

  const page = Number(pageParam || "1");
  const limit = Number(limitParam || "10");
  const skip = (page - 1) * limit;

  const response = await getMealTypes({
    limit,
    skip,
    filterCriteria: {
      active_only: active_only || undefined,
    },
  });

  return <MealTypesTable initialData={response} />;
}
