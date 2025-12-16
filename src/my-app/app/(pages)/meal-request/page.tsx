import { MealRequestForm } from './_components/meal-request-form';
import { MealRequestProvider } from './context/meal-request-context';
import { getEmployees } from '@/lib/api/employees';
import { getActiveMealTypes } from '@/lib/api/meal-types';

export default async function MealRequestPage() {
  const [employees, mealTypes] = await Promise.all([
    getEmployees(),
    getActiveMealTypes(),
  ]);

  return (
    <div className="flex flex-col h-full p-3 md:p-4">
      <MealRequestProvider mealTypes={mealTypes}>
        <MealRequestForm initialEmployees={employees} />
      </MealRequestProvider>
    </div>
  );
}
