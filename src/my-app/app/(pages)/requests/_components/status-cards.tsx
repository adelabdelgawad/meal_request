'use client';

import { useMemo } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Clock, CheckCircle, XCircle, FileText } from 'lucide-react';
import type { MealRequestStats, MealRequestStatusOption } from '@/types/meal-request.types';
import { useLanguage, translate } from '@/hooks/use-language';

interface StatusCardsProps {
  stats: MealRequestStats;
  currentStatus: string;
  statusOptions: MealRequestStatusOption[];
  onStatusClick: (status: string) => void;
}

interface StatusCardData {
  label: string;
  value: string;
  count: number;
  icon: React.ReactNode;
  color: string;
  bgColor: string;
  borderColor: string;
}

export function StatusCards({ stats, currentStatus, statusOptions, onStatusClick }: StatusCardsProps) {
  const { language: locale, t } = useLanguage();

  const statusData = useMemo<StatusCardData[]>(() => {
    // Find status IDs from statusOptions
    const pendingStatus = statusOptions.find(s => s.nameEn?.toLowerCase() === 'pending');
    const approvedStatus = statusOptions.find(s => s.nameEn?.toLowerCase() === 'approved');
    const rejectedStatus = statusOptions.find(s => s.nameEn?.toLowerCase() === 'rejected');

    return [
      {
        label: translate(t, 'requests.stats.total') || (locale === 'ar' ? 'جميع الطلبات' : 'Total Requests'),
        value: 'all',
        count: stats.total,
        icon: <FileText className="h-5 w-5" />,
        color: 'text-blue-600 dark:text-blue-400',
        bgColor: 'bg-blue-50 hover:bg-blue-100 dark:bg-blue-950 dark:hover:bg-blue-900',
        borderColor: 'border-blue-200 dark:border-blue-800',
      },
      {
        label: pendingStatus ? (locale === 'ar' ? pendingStatus.nameAr : pendingStatus.nameEn) : (translate(t, 'requests.filters.statusPending') || 'Pending'),
        value: pendingStatus ? pendingStatus.id.toString() : 'pending',
        count: stats.pending,
        icon: <Clock className="h-5 w-5" />,
        color: 'text-yellow-600 dark:text-yellow-400',
        bgColor: 'bg-yellow-50 hover:bg-yellow-100 dark:bg-yellow-950 dark:hover:bg-yellow-900',
        borderColor: 'border-yellow-200 dark:border-yellow-800',
      },
      {
        label: approvedStatus ? (locale === 'ar' ? approvedStatus.nameAr : approvedStatus.nameEn) : (translate(t, 'requests.filters.statusApproved') || 'Approved'),
        value: approvedStatus ? approvedStatus.id.toString() : 'approved',
        count: stats.approved,
        icon: <CheckCircle className="h-5 w-5" />,
        color: 'text-green-600 dark:text-green-400',
        bgColor: 'bg-green-50 hover:bg-green-100 dark:bg-green-950 dark:hover:bg-green-900',
        borderColor: 'border-green-200 dark:border-green-800',
      },
      {
        label: rejectedStatus ? (locale === 'ar' ? rejectedStatus.nameAr : rejectedStatus.nameEn) : (translate(t, 'requests.filters.statusRejected') || 'Rejected'),
        value: rejectedStatus ? rejectedStatus.id.toString() : 'rejected',
        count: stats.rejected,
        icon: <XCircle className="h-5 w-5" />,
        color: 'text-red-600 dark:text-red-400',
        bgColor: 'bg-red-50 hover:bg-red-100 dark:bg-red-950 dark:hover:bg-red-900',
        borderColor: 'border-red-200 dark:border-red-800',
      },
    ];
  }, [stats, statusOptions, locale, t]);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {statusData.map((status) => {
        const isActive = currentStatus === status.value || (!currentStatus && status.value === 'all');

        return (
          <Card
            key={status.value}
            className={`cursor-pointer transition-all duration-200 hover:scale-[1.02] ${status.bgColor} ${
              isActive ? `${status.borderColor} border-2 shadow-lg ring-2 ring-offset-2 ${status.borderColor.replace('border-', 'ring-')}` : 'border hover:shadow-md'
            }`}
            onClick={() => onStatusClick(status.value)}
          >
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{status.label}</p>
                  <p className={`text-2xl font-bold ${status.color} ${isActive ? 'animate-pulse' : ''}`}>
                    {status.count}
                  </p>
                </div>
                <div className={`${status.color} rounded-full p-2.5 shadow-sm`}>
                  {status.icon}
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
