'use client';

import { Users, FileText } from 'lucide-react';
import { useLanguage } from '@/hooks/use-language';

interface AnalysisStats {
  totalEmployees: number;
  totalRequests: number;
}

interface AnalysisStatusCardsProps {
  stats: AnalysisStats;
}

export function AnalysisStatusCards({ stats }: AnalysisStatusCardsProps) {
  const { t } = useLanguage();

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const translations = ((t?.analysis as Record<string, unknown>)?.stats || {}) as any;

  const cards = [
    {
      id: 'employees',
      label: translations?.totalEmployees || 'Total Employees',
      value: stats.totalEmployees,
      icon: Users,
      color: 'text-blue-500',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
    },
    {
      id: 'requests',
      label: translations?.totalRequests || 'Total Requests',
      value: stats.totalRequests,
      icon: FileText,
      color: 'text-green-500',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <div
            key={card.id}
            className={`
              relative overflow-hidden rounded-lg border ${card.borderColor}
              bg-card shadow-sm p-4 transition-all duration-200
              hover:shadow-md hover:scale-[1.01]
            `}
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-muted-foreground">
                  {card.label}
                </p>
                <p className={`text-3xl font-bold ${card.color} mt-1`}>
                  {card.value.toLocaleString()}
                </p>
              </div>
              <div className={`${card.bgColor} rounded-full p-3`}>
                <Icon className={`h-8 w-8 ${card.color}`} />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
