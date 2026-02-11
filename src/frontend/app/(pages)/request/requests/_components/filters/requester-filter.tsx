'use client';

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Search } from 'lucide-react';

interface RequesterFilterProps {
  value: string;
  onChange: (value: string) => void;
}

export function RequesterFilter({ value, onChange }: RequesterFilterProps) {
  return (
    <div className="w-full md:flex-1 md:min-w-[200px]">
      <Label htmlFor="requester-filter" className="text-sm font-medium">
        Requester
      </Label>
      <div className="relative mt-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          id="requester-filter"
          type="text"
          placeholder="Search Employees..."
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="pl-9"
        />
      </div>
    </div>
  );
}
