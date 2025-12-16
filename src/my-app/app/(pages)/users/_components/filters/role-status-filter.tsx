"use client";

import React from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { StatusCircle } from "@/components/data-table";
import type { SimpleRole } from "@/types/users";
import { useLanguage, translate } from "@/hooks/use-language";

interface RoleStatusFilterProps {
  roleOptions: SimpleRole[];
  _isActive?: boolean | null;
}

// Array of colors for roles (cycling through them)
const ROLE_COLORS = [
  "#3b82f6", // blue
  "#10b981", // emerald
  "#f59e0b", // amber
  "#ef4444", // red
  "#8b5cf6", // violet
  "#06b6d4", // cyan
  "#ec4899", // pink
  "#f97316", // orange
  "#6366f1", // indigo
  "#14b8a6", // teal
];

export const RoleStatusFilter: React.FC<RoleStatusFilterProps> = ({
  roleOptions,
}) => {
  const { t, language } = useLanguage();
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const currentRole = searchParams?.get("role");

  const handleRoleClick = (roleId: number) => {
    const params = new URLSearchParams(searchParams?.toString());

    if (currentRole === String(roleId)) {
      // Toggle off if already selected
      params.delete("role");
    } else {
      // Select new role
      params.set("role", String(roleId));
    }

    params.set("page", "1"); // Reset to first page
    router.push(`${pathname}?${params.toString()}`);
  };

  // Get the display name based on language
  // Supports bilingual roles with nameEn/nameAr or falls back to name
  const getRoleDisplayName = (role: SimpleRole & { nameEn?: string; nameAr?: string }) => {
    if (language === 'ar' && role.nameAr) {
      return role.nameAr;
    }
    if (language === 'en' && role.nameEn) {
      return role.nameEn;
    }
    return role.name || translate(t, 'common.noData');
  };

  if (!roleOptions || roleOptions.length === 0) {
    return (
      <div className="text-xs text-muted-foreground text-center py-2">
        {translate(t, 'statusPanel.noRolesAvailable')}
      </div>
    );
  }

  return (
    <div className="px-4 py-4">
      <div className="text-xs font-semibold text-muted-foreground mb-3">
        {translate(t, 'statusPanel.roles')}
      </div>
      <div className="flex flex-wrap gap-4 justify-center">
        {roleOptions.map((role, index) => {
          const isSelected = currentRole === String(role.id);
          const colorIndex = index % ROLE_COLORS.length;
          const color = ROLE_COLORS[colorIndex];
          const count = role.totalUsers ?? 0;
          const displayName = getRoleDisplayName(role as SimpleRole & { nameEn?: string; nameAr?: string });

          return (
            <div
              key={role.id}
              onClick={() => handleRoleClick(role.id)}
              className={`transition-all transform cursor-pointer ${
                isSelected ? "scale-110 drop-shadow-lg" : "hover:scale-105"
              }`}
              title={`${displayName} - ${translate(t, 'statusPanel.clickToFilter')}`}
              style={{ userSelect: "none" }}
            >
              <div
                className="flex flex-col items-center gap-1"
                style={{ pointerEvents: "none" }}
              >
                <StatusCircle
                  count={count}
                  color={color}
                  label={displayName}
                  size="sm"
                  showLabel={false}
                  showTooltip={false}
                />
                <span
                  className={`text-xs font-medium ${
                    isSelected ? "text-primary" : "text-muted-foreground"
                  }`}
                >
                  {displayName}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
