'use client';

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface DateFilterProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  id: string;
}

export function DateFilter({ label, value, onChange, id }: DateFilterProps) {
  return (
    <div className="w-full md:w-48">
      <Label htmlFor={id} className="text-sm font-medium">
        {label}
      </Label>
      <Input
        id={id}
        type="datetime-local"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1"
      />
    </div>
  );
}
