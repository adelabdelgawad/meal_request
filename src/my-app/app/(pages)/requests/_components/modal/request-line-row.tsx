'use client';

import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { TableCell, TableRow } from '@/components/ui/table';
import type { RequestLine } from '@/types/meal-request.types';
import { getLocalizedName } from '@/types/meal-request.types';
import { useLanguage } from '@/hooks/use-language';
import { format } from 'date-fns';

interface RequestLineRowProps {
  line: RequestLine;
  index: number;
  isDisabled: boolean;
  onAcceptedChange: (lineId: number, accepted: boolean) => void;
  onNotesChange: (lineId: number, notes: string) => void;
}

export function RequestLineRow({
  line,
  index,
  isDisabled,
  onAcceptedChange,
  onNotesChange,
}: RequestLineRowProps) {
  const shouldHighlight = !line.accepted;
  const { t, language } = useLanguage();

  // Get translations
  const lineTable = ((t?.requests as Record<string, unknown>)?.lineTable || {}) as Record<string, unknown>;

  return (
    <TableRow className={shouldHighlight ? 'bg-red-50 hover:bg-red-100 dark:bg-red-950 dark:hover:bg-red-900' : ''}>
      <TableCell className="font-medium align-middle text-center">{index + 1}</TableCell>
      <TableCell className="align-middle text-center">{line.code}</TableCell>
      <TableCell className="align-middle">{getLocalizedName(line.nameEn, line.nameAr, language) || 'N/A'}</TableCell>
      <TableCell className="align-middle">{line.title || 'N/A'}</TableCell>
      <TableCell className="align-middle">{getLocalizedName(line.departmentEn, line.departmentAr, language) || 'N/A'}</TableCell>
      <TableCell className="align-middle text-center">{line.shiftHours || 'N/A'}</TableCell>
      <TableCell className="align-middle">
        {line.signInTime
          ? format(new Date(line.signInTime), 'dd/MM/yyyy HH:mm:ss')
          : ((lineTable.notAttended as string) || 'Not Attended')}
      </TableCell>
      <TableCell className="align-middle text-center">{line.mealType}</TableCell>
      <TableCell className="align-middle text-center">
        <div className="flex justify-center">
          <Switch
            checked={line.accepted ?? true}
            disabled={isDisabled}
            onCheckedChange={(checked) =>
              onAcceptedChange(line.requestLineId, checked)
            }
            className={
              !isDisabled && (line.accepted ?? true)
                ? 'data-[state=checked]:bg-green-500'
                : ''
            }
          />
        </div>
      </TableCell>
      <TableCell className="align-middle">
        <Input
          type="text"
          value={line.notes || ''}
          disabled={isDisabled}
          onChange={(e) => onNotesChange(line.requestLineId, e.target.value)}
          className="w-full"
          placeholder={(lineTable.addNotes as string) || 'Add notes...'}
        />
      </TableCell>
    </TableRow>
  );
}
