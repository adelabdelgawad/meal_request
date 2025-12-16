'use client';

import { useEffect, useState } from 'react';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useLanguage } from '@/hooks/use-language';
import { clientApi } from '@/lib/http/axios-client';
import { Loader2 } from 'lucide-react';
import type { AuditRecord } from '@/types/analytics.types';
import { format } from 'date-fns';

interface EmployeeDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  employeeName: string;
  startTime: string;
  endTime: string;
}

export function EmployeeDetailsModal({
  isOpen,
  onClose,
  employeeName,
  startTime,
  endTime,
}: EmployeeDetailsModalProps) {
  const { t, language } = useLanguage();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<AuditRecord[]>([]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const translations = ((t?.analysis as Record<string, unknown>)?.modal || {}) as any;

  useEffect(() => {
    if (isOpen && employeeName) {
      loadEmployeeDetails();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, employeeName, startTime, endTime]);

  const loadEmployeeDetails = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (startTime) params.append('start_time', startTime);
      if (endTime) params.append('end_time', endTime);

      const response = await clientApi.get<{ data: AuditRecord[] }>(
        `/analytics/audit?${params.toString()}`
      );

      if (response.ok && response.data?.data) {
        // Filter for this specific employee (check both English and Arabic names)
        const employeeData = response.data.data.filter(
          (record) => record.employeeNameEn === employeeName || record.employeeNameAr === employeeName
        );
        setData(employeeData);
      } else {
        setData([]);
      }
    } catch (error) {
      console.error('Failed to load employee details:', error);
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  const formatDateTime = (isoString: string | null) => {
    if (!isoString) return '-';
    try {
      return format(new Date(isoString), 'M/d/yyyy h:mm a');
    } catch {
      return isoString;
    }
  };

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent className="sm:max-w-[700px] overflow-y-auto" dir={language === 'ar' ? 'rtl' : 'ltr'}>
        <SheetHeader>
          <SheetTitle>{employeeName}</SheetTitle>
          <SheetDescription>
            {translations?.description || 'Detailed meal request history for this employee'}
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : data.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              {translations?.noData || 'No meal requests found for this employee in the selected date range'}
            </div>
          ) : (
            <>
              <div className="mb-4">
                <p className="text-sm text-muted-foreground">
                  {translations?.totalRecords || 'Total Records'}: <span className="font-semibold text-foreground">{data.length}</span>
                </p>
              </div>

              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{translations?.requestTime || 'Request Time'}</TableHead>
                      <TableHead>{translations?.mealType || 'Meal Type'}</TableHead>
                      <TableHead>{translations?.requester || 'Requester'}</TableHead>
                      <TableHead>{translations?.workingHours || 'Working Hours'}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.map((record, index) => {
                      const mealType = language === 'ar' ? record.mealTypeAr : record.mealTypeEn;
                      const requester = language === 'ar' ? record.requesterAr : record.requesterEn;
                      return (
                        <TableRow key={index}>
                          <TableCell className="text-xs">
                            {formatDateTime(record.requestTime)}
                          </TableCell>
                          <TableCell>
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
                              {mealType}
                            </span>
                          </TableCell>
                          <TableCell className="text-sm">
                            <div>{requester}</div>
                            {record.requesterTitle && (
                              <div className="text-xs text-muted-foreground">{record.requesterTitle}</div>
                            )}
                          </TableCell>
                          <TableCell className="text-sm">
                            {record.workingHours !== null ? `${record.workingHours.toFixed(2)}h` : '-'}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
