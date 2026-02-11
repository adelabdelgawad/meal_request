"use client";

import { Badge } from "@/components/ui/badge";
import { ShieldCheck } from "lucide-react";
import type { UserWithRolesResponse } from "@/types/users";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface UserOverrideIndicatorProps {
  user: UserWithRolesResponse;
  language: string;
  className?: string;
}

/**
 * User Override Indicator Component
 * Displays when a user has an active status override with details
 */
export function UserOverrideIndicator({
  user,
  language,
  className = "",
}: UserOverrideIndicatorProps) {
  // Only show for users with active status override
  if (!user.statusOverride) {
    return null;
  }

  // Format the override date if available
  const overrideDate = user.overrideSetAt
    ? new Date(user.overrideSetAt).toLocaleDateString(language === "ar" ? "ar-SA" : "en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "";

  // Build tooltip content
  const tooltipContent = (
    <div className="space-y-2">
      <div className="font-semibold">
        {language === "ar" ? "تجاوز الحالة نشط" : "Status Override Active"}
      </div>
      {user.overrideReason && (
        <div>
          <div className="text-xs font-medium opacity-70">
            {language === "ar" ? "السبب:" : "Reason:"}
          </div>
          <div className="text-sm">{user.overrideReason}</div>
        </div>
      )}
      {overrideDate && (
        <div className="text-xs opacity-70">
          {language === "ar" ? "تم التعيين في:" : "Set on:"} {overrideDate}
        </div>
      )}
      <div className="text-xs opacity-70 mt-2 pt-2 border-t">
        {language === "ar"
          ? "لن يقوم مزامنة HRIS بتغيير حالة هذا المستخدم"
          : "HRIS sync will not modify this user's status"}
      </div>
    </div>
  );

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="outline"
            className={`text-xs font-medium flex items-center gap-1 bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900 dark:text-amber-300 dark:border-amber-800 ${className}`}
          >
            <ShieldCheck className="w-3 h-3" />
            <span>{language === "ar" ? "تجاوز" : "Override"}</span>
          </Badge>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-sm">
          {tooltipContent}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
