'use client';

import { useEffect, useState, useCallback, useMemo } from 'react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetFooter,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { getRequestLines } from '@/lib/api/meal-requests';
import type { MealRequest, RequestLine } from '@/types/meal-request.types';
import { Loader2, X, CheckCircle, XCircle, Clock, Calendar, FileText, User } from 'lucide-react';
import { useLanguage } from '@/hooks/use-language';
import { format } from 'date-fns';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { clientApi } from '@/lib/http/axios-client';
import { DataTable } from '@/components/data-table';
import { createHistoryLineColumns } from './history-line-columns';

interface HistoryDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  request: MealRequest;
}

// Status badge variant based on status
function getStatusBadgeVariant(statusEn: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  const status = statusEn.toLowerCase();
  if (status === 'approved') return 'default';
  if (status === 'rejected') return 'destructive';
  if (status === 'pending') return 'secondary';
  return 'outline';
}

// Status icon based on status
function StatusIcon({ status }: { status: string }) {
  const statusLower = status.toLowerCase();
  if (statusLower === 'approved') {
    return <CheckCircle className="h-4 w-4 text-green-500" />;
  }
  if (statusLower === 'rejected') {
    return <XCircle className="h-4 w-4 text-red-500" />;
  }
  return <Clock className="h-4 w-4 text-yellow-500" />;
}

export function HistoryDetailsModal({
  isOpen,
  onClose,
  request,
}: HistoryDetailsModalProps) {
  const [lines, setLines] = useState<RequestLine[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const { t, language: locale } = useLanguage();

  // Delete line state
  const [deleteLineConfirmOpen, setDeleteLineConfirmOpen] = useState(false);
  const [lineToDelete, setLineToDelete] = useState<RequestLine | null>(null);
  const [isDeletingLine, setIsDeletingLine] = useState(false);

  const isRtl = locale === 'ar';
  const isPending = request.statusNameEn === 'Pending';

  // Get translations - memoized to prevent dependency issues
  const myRequestsT = useMemo(() => (t?.myRequests || {}) as Record<string, unknown>, [t]);
  const modal = useMemo(() => (myRequestsT.modal || (t?.requests as Record<string, unknown>)?.modal || {}) as Record<string, unknown>, [myRequestsT, t]);
  const lineTable = useMemo(() => (myRequestsT.lineTable || (t?.requests as Record<string, unknown>)?.lineTable || {}) as Record<string, unknown>, [myRequestsT, t]);

  // Get localized status and meal type
  const localizedStatus = locale === 'ar' ? request.statusNameAr : request.statusNameEn;
  const localizedMealType = locale === 'ar' ? request.mealTypeAr : request.mealTypeEn;

  const loadRequestLines = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await getRequestLines(request.mealRequestId);
      setLines(data);
    } catch (error) {
      console.error('Failed to load request lines:', error);
      toast.error((modal.failedToLoad as string) || 'Failed to load details. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [request.mealRequestId, modal.failedToLoad]);

  useEffect(() => {
    if (isOpen && request.mealRequestId) {
      loadRequestLines();
    }
  }, [isOpen, request.mealRequestId, loadRequestLines]);

  // Delete line handler - show confirmation dialog
  const handleDeleteLine = useCallback((line: RequestLine) => {
    setLineToDelete(line);
    setDeleteLineConfirmOpen(true);
  }, []);

  // Confirm delete line handler
  const handleConfirmDeleteLine = useCallback(async () => {
    if (!lineToDelete || isDeletingLine) return;

    setIsDeletingLine(true);
    try {
      const response = await clientApi.delete(
        `/v1/requests/${request.mealRequestId}/lines/${lineToDelete.requestLineId}/soft-delete`
      );

      if (response.ok) {
        // Get employee name for success message
        const employeeName = (locale === 'ar' ? lineToDelete.nameAr : lineToDelete.nameEn) || 'Employee';
        const successMessage = ((myRequestsT.deleteLineSuccessMessage as string) ||
          '{{employeeName}} has been removed from the request')
          .replace('{{employeeName}}', employeeName);

        toast.success(
          (myRequestsT.deleteLineSuccess as string) || 'Employee removed successfully',
          {
            description: successMessage,
          }
        );

        // Remove the line from the local state
        setLines(prevLines => prevLines.filter(l => l.requestLineId !== lineToDelete.requestLineId));
      } else {
        toast.error(
          (myRequestsT.deleteLineError as string) || 'Failed to remove employee',
          {
            description: response.error || 'Failed to delete request line',
          }
        );
      }
    } catch (error) {
      console.error('Delete line error:', error);
      toast.error(
        (myRequestsT.deleteLineError as string) || 'Failed to remove employee',
        {
          description: 'An unexpected error occurred while deleting the line',
        }
      );
    } finally {
      setIsDeletingLine(false);
      setLineToDelete(null);
    }
  }, [lineToDelete, isDeletingLine, request.mealRequestId, locale, myRequestsT]);

  const acceptedCount = lines.filter((l) => l.accepted).length;
  const rejectedCount = lines.filter((l) => !l.accepted).length;

  // Create columns for DataTable
  const columns = useMemo(
    () => createHistoryLineColumns(
      locale,
      lineTable,
      isPending,
      isDeletingLine,
      handleDeleteLine
    ),
    [locale, lineTable, isPending, isDeletingLine, handleDeleteLine]
  );

  // Custom row className for highlighting rejected lines
  const getRowClassName = useCallback((row: RequestLine) => {
    return !row.accepted ? 'bg-red-50/50 dark:bg-red-900/10' : '';
  }, []);

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent side="right" className="w-full sm:max-w-[95vw] p-0 flex flex-col">
        <SheetHeader className="px-6 py-4 border-b">
          <div className={`flex items-center justify-between ${isRtl ? 'flex-row-reverse' : ''}`}>
            <div className={`flex items-center gap-3 ${isRtl ? 'flex-row-reverse' : ''}`}>
              <SheetTitle className={isRtl ? 'text-right' : ''}>
                {(modal.title as string) || 'Request Details'} #{request.mealRequestId}
              </SheetTitle>
              <Badge variant={getStatusBadgeVariant(request.statusNameEn)}>
                <StatusIcon status={request.statusNameEn} />
                <span className="ms-1">{localizedStatus}</span>
              </Badge>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={onClose}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* Request Summary Info */}
          <div className={`grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 p-4 bg-muted/30 rounded-lg ${isRtl ? 'text-right' : ''}`}>
            <div className={`flex items-center gap-2 ${isRtl ? 'flex-row-reverse' : ''}`}>
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">{(modal.requestTime as string) || 'Request Time'}</p>
                <p className="text-sm font-medium">
                  {format(new Date(request.requestTime), 'dd/MM/yyyy HH:mm')}
                </p>
              </div>
            </div>

            <div className={`flex items-center gap-2 ${isRtl ? 'flex-row-reverse' : ''}`}>
              <FileText className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">{(modal.mealType as string) || 'Meal Type'}</p>
                <p className="text-sm font-medium">{localizedMealType}</p>
              </div>
            </div>

            <div className={`flex items-center gap-2 ${isRtl ? 'flex-row-reverse' : ''}`}>
              <User className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">{(modal.totalEmployees as string) || 'Total Employees'}</p>
                <p className="text-sm font-medium">{request.totalRequestLines}</p>
              </div>
            </div>

            <div className={`flex items-center gap-2 ${isRtl ? 'flex-row-reverse' : ''}`}>
              <CheckCircle className="h-4 w-4 text-green-500" />
              <div>
                <p className="text-xs text-muted-foreground">{(modal.acceptedEmployees as string) || 'Accepted'}</p>
                <p className="text-sm font-medium text-green-600 dark:text-green-400">
                  {request.acceptedRequestLines ?? 0} / {request.totalRequestLines}
                </p>
              </div>
            </div>
          </div>

          {/* Closed Time Info (if closed) */}
          {request.closedTime && (
            <div className={`mt-2 p-2 bg-muted/20 rounded text-sm text-muted-foreground ${isRtl ? 'text-right' : ''}`}>
              <span>{(modal.closedOn as string) || 'Closed on'}: </span>
              <span className="font-medium">
                {format(new Date(request.closedTime), 'dd/MM/yyyy HH:mm:ss')}
              </span>
            </div>
          )}
        </SheetHeader>

        {isLoading ? (
          <div className="flex items-center justify-center flex-1 py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-auto px-6 py-4">
              {/* Stats Summary */}
              <div className={`flex gap-4 mb-4 ${isRtl ? 'flex-row-reverse' : ''}`}>
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 text-sm">
                  <CheckCircle className="h-4 w-4" />
                  <span>{acceptedCount} {(modal.accepted as string) || 'accepted'}</span>
                </div>
                {rejectedCount > 0 && (
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 text-sm">
                    <XCircle className="h-4 w-4" />
                    <span>{rejectedCount} {(modal.rejected as string) || 'rejected'}</span>
                  </div>
                )}
              </div>

              <DataTable
                _data={lines}
                columns={columns}
                _isLoading={isLoading}
                enableRowSelection={false}
                enableSorting={false}
                getRowClassName={getRowClassName}
              />
            </div>

            <SheetFooter className="px-6 py-4 border-t bg-muted/30">
              <div className={`flex items-center justify-between w-full gap-3 ${isRtl ? 'flex-row-reverse' : ''}`}>
                <div className="text-sm text-muted-foreground">
                  {(modal.viewOnlyMessage as string) || 'This is a read-only view of your request'}
                </div>
                <Button variant="outline" onClick={onClose}>
                  {(modal.close as string) || 'Close'}
                </Button>
              </div>
            </SheetFooter>
          </>
        )}

        {/* Delete Line Confirmation Dialog */}
        {lineToDelete && (
          <ConfirmDialog
            isOpen={deleteLineConfirmOpen}
            onClose={() => {
              setDeleteLineConfirmOpen(false);
              setLineToDelete(null);
            }}
            onConfirm={handleConfirmDeleteLine}
            title={((myRequestsT.deleteLine as Record<string, unknown>)?.title as string) || 'Delete Employee Line?'}
            message={
              ((myRequestsT.deleteLine as Record<string, unknown>)?.message as string ||
                'Are you sure you want to remove {{employeeName}} from this request? This action cannot be undone.')
                .replace('{{employeeName}}', (locale === 'ar' ? lineToDelete.nameAr : lineToDelete.nameEn) || 'Employee')
            }
            confirmText={((myRequestsT.deleteLine as Record<string, unknown>)?.confirm as string) || 'Delete'}
            cancelText={((myRequestsT.deleteLine as Record<string, unknown>)?.cancel as string) || 'Cancel'}
            isRtl={isRtl}
            variant="destructive"
            isLoading={isDeletingLine}
          />
        )}
      </SheetContent>
    </Sheet>
  );
}
