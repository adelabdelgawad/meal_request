'use client';

import { ColumnDef } from '@tanstack/react-table';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import type { RequestLine } from '@/types/meal-request.types';
import { getLocalizedName } from '@/types/meal-request.types';
import { format } from 'date-fns';

interface ColumnTranslations {
  rowNum?: string;
  code?: string;
  employeeName?: string;
  title?: string;
  department?: string;
  shift?: string;
  attendanceTime?: string;
  type?: string;
  accepted?: string;
  notes?: string;
  notAttended?: string;
  addNotes?: string;
}

export function createRequestLineColumns(
  locale: string,
  translations: ColumnTranslations,
  isDisabled: boolean,
  onAcceptedChange: (lineId: number, accepted: boolean) => void,
  onNotesChange: (lineId: number, notes: string) => void
): ColumnDef<RequestLine>[] {
  return [
    {
      id: 'rowNum',
      header: translations.rowNum || '#',
      size: 50,
      minSize: 40,
      maxSize: 60,
      cell: ({ row }) => (
        <div className="font-medium">{row.index + 1}</div>
      ),
    },
    {
      id: 'code',
      accessorKey: 'code',
      header: translations.code || 'Code',
      size: 80,
      minSize: 60,
      maxSize: 100,
    },
    {
      id: 'employeeName',
      header: translations.employeeName || 'Employee Name',
      size: 200,
      minSize: 150,
      maxSize: 300,
      cell: ({ row }) => (
        <div className="truncate">
          {getLocalizedName(row.original.nameEn, row.original.nameAr, locale) || 'N/A'}
        </div>
      ),
    },
    {
      id: 'title',
      accessorKey: 'title',
      header: translations.title || 'Title',
      size: 150,
      minSize: 100,
      maxSize: 200,
      cell: ({ row }) => (
        <div className="truncate">{row.original.title || 'N/A'}</div>
      ),
    },
    {
      id: 'department',
      header: translations.department || 'Department',
      size: 150,
      minSize: 100,
      maxSize: 250,
      cell: ({ row }) => (
        <div className="truncate">
          {getLocalizedName(row.original.departmentEn, row.original.departmentAr, locale) || 'N/A'}
        </div>
      ),
    },
    {
      id: 'shift',
      accessorKey: 'shiftHours',
      header: translations.shift || 'Shift',
      size: 70,
      minSize: 60,
      maxSize: 100,
      cell: ({ row }) => (
        <div>{row.original.shiftHours || 'N/A'}</div>
      ),
    },
    {
      id: 'attendanceTime',
      header: translations.attendanceTime || 'Attendance Time',
      size: 180,
      minSize: 150,
      maxSize: 220,
      cell: ({ row }) => (
        <div className="truncate">
          {row.original.signInTime
            ? format(new Date(row.original.signInTime), 'dd/MM/yyyy HH:mm:ss')
            : (translations.notAttended || 'Not Attended')}
        </div>
      ),
    },
    {
      id: 'mealType',
      accessorKey: 'mealType',
      header: translations.type || 'Type',
      size: 80,
      minSize: 60,
      maxSize: 120,
    },
    {
      id: 'accepted',
      header: translations.accepted || 'Accepted',
      size: 100,
      minSize: 80,
      maxSize: 120,
      cell: ({ row }) => (
        <div className="flex justify-center">
          <Switch
            checked={row.original.accepted ?? true}
            disabled={isDisabled}
            onCheckedChange={(checked) =>
              onAcceptedChange(row.original.requestLineId, checked)
            }
            className={
              !isDisabled && (row.original.accepted ?? true)
                ? 'data-[state=checked]:bg-green-500'
                : ''
            }
          />
        </div>
      ),
    },
    {
      id: 'notes',
      header: translations.notes || 'Notes',
      size: 200,
      minSize: 150,
      maxSize: 300,
      cell: ({ row }) => (
        <Input
          type="text"
          value={row.original.notes || ''}
          disabled={isDisabled}
          onChange={(e) => onNotesChange(row.original.requestLineId, e.target.value)}
          className="w-full"
          placeholder={translations.addNotes || 'Add notes...'}
        />
      ),
    },
  ];
}
