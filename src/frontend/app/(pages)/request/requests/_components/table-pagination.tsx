'use client';

import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useLanguage } from '@/hooks/use-language';

interface TablePaginationProps {
  currentPage: number;
  totalPages: number;
  total: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

export function TablePagination({
  currentPage,
  totalPages,
  total,
  pageSize,
  onPageChange,
}: TablePaginationProps) {
  const { t } = useLanguage();

  // Get translations - t.requests.pagination is expected to have pagination strings
  const requestsTranslations = (t as Record<string, unknown>)?.requests as Record<string, unknown> | undefined;
  const pagination = (requestsTranslations?.pagination || {}) as Record<string, unknown>;

  const startItem = totalPages === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, total);

  const canGoPrevious = currentPage > 1;
  const canGoNext = currentPage < totalPages;

  return (
    <div className="flex items-center justify-between px-6 py-4 border-t bg-muted/50">
      <div className="text-sm text-muted-foreground">
        {(pagination.showing as string) || 'Showing'} <span className="font-medium">{startItem}</span> {(pagination.to as string) || 'to'}{' '}
        <span className="font-medium">{endItem}</span> {(pagination.of as string) || 'of'}{' '}
        <span className="font-medium">{total}</span> {(pagination.results as string) || 'results'}
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(1)}
          disabled={!canGoPrevious}
          className="h-8 w-8 p-0"
        >
          <ChevronsLeft className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={!canGoPrevious}
          className="h-8 w-8 p-0"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>

        <div className="flex items-center gap-1">
          <span className="text-sm">
            {(pagination.page as string) || 'Page'} <span className="font-medium">{currentPage}</span> {(pagination.of as string) || 'of'}{' '}
            <span className="font-medium">{totalPages || 1}</span>
          </span>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={!canGoNext}
          className="h-8 w-8 p-0"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(totalPages)}
          disabled={!canGoNext}
          className="h-8 w-8 p-0"
        >
          <ChevronsRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
