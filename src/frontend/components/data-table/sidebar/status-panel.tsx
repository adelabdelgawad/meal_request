"use client";

import React, { useState, ReactNode } from "react";
import { ChevronLeft, ChevronRight, LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatusCircle } from "../ui/status-circle";
import { useLanguage, translate } from "@/hooks/use-language";

export interface StatusItem {
  count: number;
  color: string;
  label: string;
  statusValue: string;
}

export interface StatusPanelProps {
  /** Total count of all items */
  totalCount: number;
  /** Number of active items */
  activeCount: number;
  /** Number of inactive items */
  inactiveCount: number;
  /** Label for the entity (e.g., "User", "Role") */
  entityLabel: string;
  /** Icon to display in the main status circle */
  icon: LucideIcon;
  /** Query param name for filtering (default: "is_active") */
  queryParam?: string;
  /** Optional extra content to render when expanded (e.g., role filters) */
  extraContent?: ReactNode;
  /** Default expanded state */
  defaultExpanded?: boolean;
}

/**
 * Reusable status panel sidebar component for data tables.
 * Shows counts for all, active, and inactive items with optional filtering.
 */
export const StatusPanel: React.FC<StatusPanelProps> = ({
  totalCount,
  activeCount,
  inactiveCount,
  entityLabel,
  icon,
  queryParam = "is_active",
  extraContent,
  defaultExpanded = false,
}) => {
  const { t, dir } = useLanguage();
  const isRtl = dir === "rtl";
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const activePercentage = totalCount ? (activeCount / totalCount) * 100 : 0;
  const totalColor = totalCount > 1 ? "#6b7280" : "#ef4444";

  // Translate entity label
  const getTranslatedEntityLabel = () => {
    if (entityLabel.toLowerCase() === "user") {
      return translate(t, "statusPanel.user");
    }
    if (entityLabel.toLowerCase() === "role") {
      return translate(t, "statusPanel.role");
    }
    return entityLabel;
  };

  const translatedActiveLabel = translate(t, "statusPanel.active");
  const translatedInactiveLabel = translate(t, "statusPanel.inactive");
  const translatedAllLabel = translate(t, "statusPanel.all");

  // RTL-aware toggle button position
  const getToggleButtonPosition = () => {
    if (isRtl) {
      return isExpanded ? "-left-3" : "right-0";
    }
    return isExpanded ? "-right-3" : "left-0";
  };

  // RTL-aware chevron icons
  const ExpandIcon = isRtl ? ChevronLeft : ChevronRight;
  const CollapseIcon = isRtl ? ChevronRight : ChevronLeft;

  return (
    <div
      className={`bg-card shadow-lg h-full shrink-0 flex flex-col transition-all duration-300 relative min-h-0 border-e border-border ${
        isExpanded ? "w-80" : "w-20"
      }`}
    >
      {/* Toggle Arrow Button */}
      <div
        className={`absolute top-1/2 -translate-y-1/2 z-20 transition-all ${getToggleButtonPosition()}`}
      >
        <Button
          onClick={() => setIsExpanded(!isExpanded)}
          size="icon"
          variant="ghost"
          className="w-6 h-12 bg-card hover:bg-muted transition-all p-0 border border-border shadow-sm"
        >
          {isExpanded ? (
            <CollapseIcon className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ExpandIcon className="h-4 w-4 text-muted-foreground" />
          )}
        </Button>
      </div>

      {/* Content */}
      <div className="flex-1 flex flex-col overflow-y-auto p-4">
        {isExpanded ? (
          <>
            <div className="px-4 py-6">
              <div className="flex flex-col items-center">
                <StatusCircle
                  count={totalCount}
                  color={totalColor}
                  label={getTranslatedEntityLabel()}
                  size="lg"
                  icon={icon}
                  showLabel={true}
                  percentage={activePercentage}
                  statusValue="all"
                  queryParam={queryParam}
                />
              </div>
            </div>
            <div className="px-4 pb-6">
              <div className="grid grid-cols-2 gap-12">
                <StatusCircle
                  count={activeCount}
                  color="#22c55e"
                  label={translatedActiveLabel}
                  size="md"
                  statusValue="true"
                  queryParam={queryParam}
                />
                <StatusCircle
                  count={inactiveCount}
                  color="#ef4444"
                  label={translatedInactiveLabel}
                  size="md"
                  statusValue="false"
                  queryParam={queryParam}
                />
              </div>
            </div>
            {/* Extra Content (e.g., filters) */}
            {extraContent && (
              <div className="border-t border-border">{extraContent}</div>
            )}
          </>
        ) : (
          <>
            <div className="py-3 border-b border-border flex justify-center">
              <StatusCircle
                count={totalCount}
                color={totalColor}
                label={`${translatedAllLabel} ${getTranslatedEntityLabel()}`}
                size="sm"
                showLabel={false}
                showTooltip={true}
                statusValue="all"
                queryParam={queryParam}
              />
            </div>
            <div className="py-3 border-b border-border flex justify-center">
              <StatusCircle
                count={activeCount}
                color="#22c55e"
                label={translatedActiveLabel}
                size="sm"
                showLabel={false}
                showTooltip={true}
                statusValue="true"
                queryParam={queryParam}
              />
            </div>
            <div className="py-3 border-b border-border flex justify-center">
              <StatusCircle
                count={inactiveCount}
                color="#ef4444"
                label={translatedInactiveLabel}
                size="sm"
                showLabel={false}
                showTooltip={true}
                statusValue="false"
                queryParam={queryParam}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
};
