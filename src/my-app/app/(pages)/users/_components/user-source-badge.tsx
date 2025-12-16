"use client";

import { Badge } from "@/components/ui/badge";
import { Database, UserPen } from "lucide-react";
import type { UserSourceMetadata } from "@/types/users";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface UserSourceBadgeProps {
  userSource: string;
  userSourceMetadata?: UserSourceMetadata | null;
  language: string;
  className?: string;
}

/**
 * User Source Badge Component
 * Displays the source of a user (HRIS/Manual) with localized labels, colors, and icons
 */
export function UserSourceBadge({
  userSource,
  userSourceMetadata,
  language,
  className = "",
}: UserSourceBadgeProps) {
  // If no metadata provided, use defaults
  const metadata = userSourceMetadata || {
    code: userSource,
    nameEn: userSource.toUpperCase(),
    nameAr: userSource.toUpperCase(),
    descriptionEn: `User source: ${userSource}`,
    descriptionAr: `مصدر المستخدم: ${userSource}`,
    icon: userSource === "hris" ? "database" : "user-edit",
    color: userSource === "hris" ? "blue" : "green",
    canOverride: userSource === "hris",
  };

  // Get localized label
  const label = language === "ar" ? metadata.nameAr : metadata.nameEn;
  const description = language === "ar" ? metadata.descriptionAr : metadata.descriptionEn;

  // Get icon based on metadata
  const Icon = metadata.icon === "database" ? Database : UserPen;

  // Get color classes based on metadata color
  const colorClasses = {
    blue: "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900 dark:text-blue-300 dark:border-blue-800",
    green: "bg-green-100 text-green-700 border-green-200 dark:bg-green-900 dark:text-green-300 dark:border-green-800",
    gray: "bg-gray-100 text-gray-700 border-gray-200 dark:bg-gray-900 dark:text-gray-300 dark:border-gray-800",
  }[metadata.color] || "bg-gray-100 text-gray-700 border-gray-200";

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="outline"
            className={`text-xs font-medium flex items-center gap-1 ${colorClasses} ${className}`}
          >
            <Icon className="w-3 h-3" />
            <span>{label}</span>
          </Badge>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs">
          <p className="text-sm">{description}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
