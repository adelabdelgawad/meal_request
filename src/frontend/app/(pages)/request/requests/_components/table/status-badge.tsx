import { Badge } from '@/components/ui/badge';
import { REQUEST_STATUS_COLORS } from '@/types/meal-request.types';

interface StatusBadgeProps {
  status: string;
  label?: string; // Optional localized label
}

export function StatusBadge({ status, label }: StatusBadgeProps) {
  const normalizedStatus = status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
  const colorClass =
    REQUEST_STATUS_COLORS[normalizedStatus as keyof typeof REQUEST_STATUS_COLORS] ||
    'bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-800 dark:text-gray-200 dark:border-gray-700';

  const displayText = label || normalizedStatus;

  return (
    <Badge variant="outline" className={`${colorClass} font-semibold`}>
      {displayText}
    </Badge>
  );
}
