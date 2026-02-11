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
import { updateRequestLine } from '@/lib/actions/requests.actions';
import type { RequestLine } from '@/types/meal-request.types';
import { Loader2, X } from 'lucide-react';
import { useLanguage } from '@/hooks/use-language';
import { DataTable } from '@/components/data-table';
import { createRequestLineColumns } from './request-line-columns';

interface RequestDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  requestId: number;
  requestStatus: string;
  userId: string;
  onSaveSuccess: () => void;
  initialLines?: RequestLine[];
}

interface ModifiedLine {
  id: number;
  accepted: boolean;
  notes: string;
}

export function RequestDetailsModal({
  isOpen,
  onClose,
  requestId,
  requestStatus,
  userId,
  onSaveSuccess,
  initialLines,
}: RequestDetailsModalProps) {
  const [lines, setLines] = useState<RequestLine[]>(initialLines || []);
  const [originalLines, setOriginalLines] = useState<ModifiedLine[]>([]);
  const [isLoading, setIsLoading] = useState(!initialLines);
  const [isSaving, setIsSaving] = useState(false);
  const { t, language: locale } = useLanguage();

  const isPending = requestStatus.toLowerCase() === 'pending';

  // Get translations - memoized to prevent dependency issues
  const modal = useMemo(() => ((t?.requests as Record<string, unknown>)?.modal || {}) as Record<string, unknown>, [t]);
  const lineTable = useMemo(() => ((t?.requests as Record<string, unknown>)?.lineTable || {}) as Record<string, unknown>, [t]);

  const loadRequestLines = useCallback(async () => {
    // Only fetch if no initial lines provided (backward compatibility)
    if (initialLines && initialLines.length > 0) {
      return;
    }

    setIsLoading(true);
    try {
      const data = await getRequestLines(requestId);
      setLines(data);
      setOriginalLines(
        data.map((line) => ({
          id: line.requestLineId,
          accepted: line.accepted ?? true,
          notes: line.notes || '',
        }))
      );
    } catch (error) {
      console.error('Failed to load request lines:', error);
      toast.error((modal.failedToLoad as string) || 'Failed to load details. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [requestId, initialLines, modal.failedToLoad]);

  useEffect(() => {
    if (isOpen && requestId) {
      if (initialLines && initialLines.length > 0) {
        // Use prefetched lines immediately
        setLines(initialLines);
        setOriginalLines(
          initialLines.map((line) => ({
            id: line.requestLineId,
            accepted: line.accepted ?? true,
            notes: line.notes || '',
          }))
        );
        setIsLoading(false);
      } else {
        // Fallback to fetching (backward compatibility)
        loadRequestLines();
      }
    }
  }, [isOpen, requestId, initialLines, loadRequestLines]);

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setLines([]);
      setOriginalLines([]);
      setIsLoading(true);
    }
  }, [isOpen]);

  const handleAcceptedChange = useCallback((lineId: number, accepted: boolean) => {
    setLines((prev) =>
      prev.map((line) => (line.requestLineId === lineId ? { ...line, accepted } : line))
    );
  }, []);

  const handleNotesChange = useCallback((lineId: number, notes: string) => {
    setLines((prev) =>
      prev.map((line) => (line.requestLineId === lineId ? { ...line, notes } : line))
    );
  }, []);

  const handleSave = async () => {
    if (!isPending) return;

    // Find modified lines
    const modifiedLines = lines.filter((line) => {
      const original = originalLines.find((o) => o.id === line.requestLineId);
      if (!original) return false;
      return (
        original.accepted !== (line.accepted ?? true) ||
        original.notes !== (line.notes || '')
      );
    });

    if (modifiedLines.length === 0) {
      toast.info((modal.noChanges as string) || 'No changes to save');
      onClose();
      return;
    }

    setIsSaving(true);
    const errors: string[] = [];

    try {
      for (const line of modifiedLines) {
        const result = await updateRequestLine({
          userId,
          mealRequestLineId: line.requestLineId,
          accepted: line.accepted ?? true,
          notes: line.notes || '',
        });

        if (!result.success) {
          errors.push(`Request line ${line.requestLineId} failed to update.`);
        }
      }

      if (errors.length > 0) {
        toast.error(errors.join('\n'));
      } else {
        toast.success((modal.allChangesSaved as string) || 'All changes saved successfully');
        onSaveSuccess();
        onClose();
      }
    } catch (error) {
      console.error('Failed to save changes:', error);
      toast.error((modal.failedToSave as string) || 'Failed to save changes. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  // Create columns for DataTable
  const columns = useMemo(
    () => createRequestLineColumns(
      locale,
      lineTable,
      !isPending,
      handleAcceptedChange,
      handleNotesChange
    ),
    [locale, lineTable, isPending, handleAcceptedChange, handleNotesChange]
  );

  // Custom row className for highlighting rejected lines
  const getRowClassName = useCallback((row: RequestLine) => {
    return !row.accepted ? 'bg-red-50 hover:bg-red-100 dark:bg-red-950 dark:hover:bg-red-900' : '';
  }, []);

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent side="right" className="w-full sm:max-w-[95vw] p-0 flex flex-col">
        <SheetHeader className="px-6 py-4 border-b">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <SheetTitle>{(modal.title as string) || 'Request Details'}</SheetTitle>
              <Badge variant={isPending ? 'default' : 'secondary'}>
                {requestStatus}
              </Badge>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={onClose}
              disabled={isSaving}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          {lines.length > 0 && (
            <p className="text-sm text-muted-foreground mt-2">
              {lines.length} {lines.length !== 1 ? ((modal.employees as string) || 'employees') : ((modal.employee as string) || 'employee')} • {lines.filter((l) => l.accepted).length} {(modal.accepted as string) || 'accepted'}
            </p>
          )}
        </SheetHeader>

        {isLoading ? (
          <div className="flex items-center justify-center flex-1 py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-auto px-6 py-4">
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
              <div className="flex items-center justify-between w-full gap-3">
                <div className="text-sm text-muted-foreground">
                  {isPending ? ((modal.editMessage as string) || 'You can edit and save changes') : ((modal.viewOnlyMessage as string) || 'Request is closed - view only')}
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={onClose} disabled={isSaving}>
                    {isPending ? ((modal.cancel as string) || 'Cancel') : ((modal.close as string) || 'Close')}
                  </Button>
                  {isPending && (
                    <Button onClick={handleSave} disabled={isSaving}>
                      {isSaving ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          {(modal.saving as string) || 'Saving...'}
                        </>
                      ) : (
                        (modal.saveChanges as string) || 'Save Changes'
                      )}
                    </Button>
                  )}
                </div>
              </div>
            </SheetFooter>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
