'use client';

import { Search, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';

interface EnhancedRequesterFilterProps {
  value: string;
  onChange: (value: string) => void;
}

export function EnhancedRequesterFilter({ value, onChange }: EnhancedRequesterFilterProps) {
  const handleClear = () => {
    onChange('');
  };

  return (
    <div className="w-full">
      <Label htmlFor="requester-search" className="text-sm font-medium mb-1.5 block">
        Search Requester
      </Label>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          id="requester-search"
          type="text"
          placeholder="Search by name..."
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="pl-10 pr-10"
        />
        {value && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleClear}
            className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7 p-0 hover:bg-gray-200"
          >
            <X className="h-3 w-3" />
          </Button>
        )}
      </div>
      <p className="text-xs text-muted-foreground mt-1">
        {value ? `Filtering by: "${value}"` : 'Search by requester name'}
      </p>
    </div>
  );
}
