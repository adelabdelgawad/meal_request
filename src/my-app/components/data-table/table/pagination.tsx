"use client";

import React, { useTransition } from "react";
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import { useQueryState, parseAsInteger } from "nuqs";
import { useLanguage } from "@/hooks/use-language";

interface PaginationProps {
  currentPage?: number;
  pageSize?: number;
  totalItems?: number;
  totalPages?: number;
}

export const Pagination: React.FC<PaginationProps> = ({
  currentPage: initialPage,
  pageSize: initialPageSize,
  totalItems = 0,
  totalPages: initialTotalPages,
}) => {
  const { language, dir } = useLanguage();
  const isRtl = dir === 'rtl';

  const [page, setPage] = useQueryState(
    "page",
    parseAsInteger.withDefault(1)
  );

  const [limit, setLimit] = useQueryState(
    "limit",
    parseAsInteger.withDefault(10)
  );

  const [, startTransition] = useTransition();

  // Use props if provided, otherwise use URL state
  const currentPage = initialPage ?? page;
  const pageSize = initialPageSize ?? limit;
  const totalPages = Math.max(1, initialTotalPages ?? Math.ceil(totalItems / pageSize));

  const startItem = totalItems > 0 ? (currentPage - 1) * pageSize + 1 : 0;
  const endItem = Math.min(currentPage * pageSize, totalItems);

  // i18n labels
  const labels = {
    showing: language === 'ar' ? 'عرض' : 'Showing',
    to: language === 'ar' ? 'إلى' : 'to',
    of: language === 'ar' ? 'من' : 'of',
    entries: language === 'ar' ? 'إدخال' : 'entries',
    rowsPerPage: language === 'ar' ? 'صفوف في الصفحة:' : 'Rows per page:',
    goToFirstPage: language === 'ar' ? 'الذهاب للصفحة الأولى' : 'Go to first page',
    goToLastPage: language === 'ar' ? 'الذهاب للصفحة الأخيرة' : 'Go to last page',
  };

  const handlePageChange = async (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      startTransition(async () => {
        await setPage(newPage === 1 ? null : newPage);
        // No router.refresh() needed - SWR will auto-refetch!
      });
    }
  };

  const handlePageSizeChange = async (newSize: number) => {
    startTransition(async () => {
      await setLimit(newSize === 10 ? null : newSize);
      await setPage(null); // Reset to page 1
      // No router.refresh() needed - SWR will auto-refetch!
    });
  };

  // Icons stay the same - flex-row-reverse handles the visual order
  const FirstPageIcon = ChevronsLeft;
  const LastPageIcon = ChevronsRight;
  const PrevPageIcon = ChevronLeft;
  const NextPageIcon = ChevronRight;

  return (
    <div className={`flex items-center justify-between px-4 py-3 bg-card border-t border-border ${isRtl ? 'flex-row-reverse' : ''}`}>
      <div className={`flex items-center gap-4 ${isRtl ? 'flex-row-reverse' : ''}`}>
        <span className="text-sm text-muted-foreground">
          {labels.showing} {startItem} {labels.to} {endItem} {labels.of} {totalItems} {labels.entries}
        </span>
        <div className={`flex items-center gap-2 ${isRtl ? 'flex-row-reverse' : ''}`}>
          <label className="text-sm text-muted-foreground">{labels.rowsPerPage}</label>
          <select
            value={pageSize}
            onChange={(e) => handlePageSizeChange(Number(e.target.value))}
            className="border border-border px-2 py-1 text-sm bg-background text-foreground"
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
      </div>
      <div className={`flex items-center gap-2 ${isRtl ? 'flex-row-reverse' : ''}`}>
        {/* Go to First Page Button */}
        <button
          onClick={() => handlePageChange(1)}
          disabled={currentPage === 1 || totalItems === 0}
          className="p-2 border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed text-foreground"
          title={labels.goToFirstPage}
        >
          <FirstPageIcon className="w-4 h-4" />
        </button>
        {/* Previous Page Button */}
        <button
          onClick={() => handlePageChange(currentPage - 1)}
          disabled={currentPage === 1 || totalItems === 0}
          className="p-2 border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed text-foreground"
        >
          <PrevPageIcon className="w-4 h-4" />
        </button>
        {/* Page numbers */}
        <div className={`flex gap-1 ${isRtl ? 'flex-row-reverse' : ''}`}>
          {[...Array(totalPages)].map((_, i) => {
            const pageNum = i + 1;
            if (
              pageNum === 1 ||
              pageNum === totalPages ||
              (pageNum >= currentPage - 1 && pageNum <= currentPage + 1)
            ) {
              return (
                <button
                  key={pageNum}
                  onClick={() => handlePageChange(pageNum)}
                  className={`px-3 py-1 text-sm ${
                    currentPage === pageNum
                      ? "bg-primary text-primary-foreground"
                      : "border border-border hover:bg-muted text-foreground"
                  }`}
                >
                  {pageNum}
                </button>
              );
            } else if (
              pageNum === currentPage - 2 ||
              pageNum === currentPage + 2
            ) {
              return (
                <span key={pageNum} className="px-2 text-muted-foreground">
                  ...
                </span>
              );
            }
            return null;
          })}
        </div>
        {/* Next Page Button */}
        <button
          onClick={() => handlePageChange(currentPage + 1)}
          disabled={currentPage === totalPages || totalItems === 0}
          className="p-2 border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed text-foreground"
        >
          <NextPageIcon className="w-4 h-4" />
        </button>
        {/* Go to Last Page Button */}
        <button
          onClick={() => handlePageChange(totalPages)}
          disabled={currentPage === totalPages || totalItems === 0}
          className="p-2 border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed text-foreground"
          title={labels.goToLastPage}
        >
          <LastPageIcon className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};