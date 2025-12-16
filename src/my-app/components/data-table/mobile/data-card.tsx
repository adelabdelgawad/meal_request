"use client";

import React from 'react';
import { Card, CardContent } from '@/components/ui/card';

export interface DataCardField {
  label: string;
  value: React.ReactNode;
  className?: string;
  fullWidth?: boolean;
}

export interface DataCardAction {
  label: string;
  onClick: () => void;
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  icon?: React.ReactNode;
  disabled?: boolean;
}

interface DataCardProps {
  title?: React.ReactNode;
  badge?: React.ReactNode;
  fields: DataCardField[];
  actions?: DataCardAction[];
  onClick?: () => void;
  className?: string;
}

/**
 * Mobile-optimized card component for displaying table row data.
 * Shows key information in a card format instead of table columns.
 */
export function DataCard({
  title,
  badge,
  fields,
  actions,
  onClick,
  className = '',
}: DataCardProps) {
  return (
    <Card
      className={`transition-colors hover:bg-accent/50 ${onClick ? 'cursor-pointer' : ''} ${className}`}
      onClick={onClick}
    >
      <CardContent className="p-4">
        {/* Header with title and badge */}
        {(title || badge) && (
          <div className="flex items-start justify-between gap-2 mb-3 pb-3 border-b">
            {title && (
              <div className="font-semibold text-base min-w-0 flex-1">
                {title}
              </div>
            )}
            {badge && <div className="shrink-0">{badge}</div>}
          </div>
        )}

        {/* Fields grid */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-3">
          {fields.map((field, index) => (
            <div
              key={index}
              className={`${field.fullWidth ? 'col-span-2' : ''}`}
            >
              <div className="text-xs text-muted-foreground mb-1">
                {field.label}
              </div>
              <div className={`text-sm ${field.className || ''}`}>
                {field.value}
              </div>
            </div>
          ))}
        </div>

        {/* Actions */}
        {actions && actions.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-4 pt-3 border-t">
            {actions.map((action, index) => (
              <button
                key={index}
                onClick={(e) => {
                  e.stopPropagation();
                  action.onClick();
                }}
                disabled={action.disabled}
                className={`
                  inline-flex items-center justify-center gap-1.5 rounded-md px-3 py-1.5
                  text-sm font-medium transition-colors
                  disabled:pointer-events-none disabled:opacity-50
                  ${action.variant === 'destructive' ? 'bg-destructive text-destructive-foreground hover:bg-destructive/90' : ''}
                  ${action.variant === 'outline' ? 'border border-input bg-background hover:bg-accent hover:text-accent-foreground' : ''}
                  ${action.variant === 'secondary' ? 'bg-secondary text-secondary-foreground hover:bg-secondary/80' : ''}
                  ${action.variant === 'ghost' ? 'hover:bg-accent hover:text-accent-foreground' : ''}
                  ${!action.variant || action.variant === 'default' ? 'bg-primary text-primary-foreground hover:bg-primary/90' : ''}
                `}
              >
                {action.icon}
                {action.label}
              </button>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
