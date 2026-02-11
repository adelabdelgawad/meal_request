"use client";

import { useMemo } from "react";
import { TableHeader, type ValueFormatter } from "@/components/data-table";
import type { UserWithRolesResponse, SimpleRole } from "@/types/users";
import { useLanguage, translate } from "@/hooks/use-language";

interface UsersTableHeaderProps {
  page: number;
  tableInstance: import("@tanstack/react-table").Table<UserWithRolesResponse> | null;
  roleOptions?: SimpleRole[];
}

/**
 * Header section of the users table with search and export controls
 */
export function UsersTableHeader({
  page,
  tableInstance,
  roleOptions = [],
}: UsersTableHeaderProps) {
  const { t, language } = useLanguage();

  // Create a map of role IDs to names for quick lookup
  const roleMap = useMemo(() => {
    const map = new Map<number, string>();
    roleOptions.forEach((role) => {
      const name = language === "ar" && role.nameAr ? role.nameAr : (role.nameEn || role.name);
      map.set(role.id, name);
    });
    return map;
  }, [roleOptions, language]);

  // Value formatters for export
  const exportValueFormatters = useMemo<Record<string, ValueFormatter<UserWithRolesResponse>>>(() => ({
    // Format roles column: convert role IDs to names
    roles: (_value, row) => {
      const roleIds = row.roleIds || [];
      if (roleIds.length === 0) {
        return translate(t, 'table.noRoles');
      }
      return roleIds
        .map((id) => roleMap.get(id) || id)
        .join("; ");
    },
    // Format isActive column
    isActive: (value) => {
      return value ? translate(t, 'common.yes') : translate(t, 'common.no');
    },
  }), [roleMap, t]);

  // Header labels for export (translated)
  const exportHeaderLabels = useMemo(() => ({
    username: translate(t, 'users.columns.username'),
    fullName: translate(t, 'users.columns.fullName'),
    email: translate(t, 'users.columns.email'),
    title: translate(t, 'users.columns.title'),
    isActive: translate(t, 'users.columns.active'),
    roles: translate(t, 'users.columns.roles'),
  }), [t]);

  return (
    <TableHeader
      page={page}
      tableInstance={tableInstance}
      searchPlaceholder={translate(t, 'users.searchPlaceholder')}
      searchUrlParam="search"
      exportFilename={translate(t, 'users.exportFilename')}
      printTitle={translate(t, 'users.printTitle')}
      exportValueFormatters={exportValueFormatters}
      exportHeaderLabels={exportHeaderLabels}
    />
  );
}
