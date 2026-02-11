"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Badge } from "@/components/ui/badge";
import { StatusSwitch } from "@/components/ui/status-switch";
import { Loader2, User as UserIcon, Building2 } from "lucide-react";
import { toast } from "@/components/ui/custom-toast";
import { toggleUserStatus, toggleUserBlock } from "@/lib/api/users";
import type { UserWithRolesResponse, SimpleRole } from "@/types/users";
import { UserSourceBadge } from "../user-source-badge";
import { UserOverrideIndicator } from "../user-override-indicator";

interface ColumnTranslations {
  username: string;
  fullName: string;
  email: string;
  title: string;
  source: string;
  override: string;
  active: string;
  blocked: string;
  roles: string;
  departments: string;
  allDepartments: string;
  actions: string;
  noRoles: string;
  activateUser: string;
  deactivateUser: string;
  activateMessage: string;
  deactivateMessage: string;
  activateSuccess: string;
  deactivateSuccess: string;
  blockUser: string;
  unblockUser: string;
  blockMessage: string;
  unblockMessage: string;
  blockSuccess: string;
  unblockSuccess: string;
}

interface UsersTableColumnsProps {
  updatingIds: Set<string>;
  mutate: () => void;
  updateUsers: (users: UserWithRolesResponse[]) => Promise<void>;
  markUpdating: (ids: string[]) => void;
  clearUpdating: (ids?: string[]) => void;
  translations: ColumnTranslations;
  roleOptions: SimpleRole[];
  language: string;
}

/**
 * Get role display name based on language
 */
function getRoleDisplayName(
  roleId: number,
  roleOptions: SimpleRole[],
  language: string
): string {
  const role = roleOptions.find((r) => r.id === roleId);
  if (!role) return String(roleId);
  if (language === "ar" && role.nameAr) return role.nameAr;
  if (role.nameEn) return role.nameEn;
  return role.name;
}

/**
 * Create column definitions for the users table
 */
export function createUsersTableColumns({
  updatingIds,
  mutate,
  updateUsers,
  markUpdating,
  clearUpdating,
  translations: t,
  roleOptions,
  language,
}: UsersTableColumnsProps): ColumnDef<UserWithRolesResponse>[] {
  return [
    {
      id: "select",
      header: ({ table }) => (
        <div className="flex justify-center">
          <input
            type="checkbox"
            className="border-gray-300 cursor-pointer"
            checked={table.getIsAllPageRowsSelected()}
            onChange={(e) => table.toggleAllPageRowsSelected(e.target.checked)}
            disabled={updatingIds.size > 0}
          />
        </div>
      ),
      cell: ({ row }) => {
        const isRowUpdating = Boolean(
          row.original.id && updatingIds.has(row.original.id)
        );

        return (
          <div
            className={`flex justify-center items-center px-2 ${
              isRowUpdating ? "opacity-60" : ""
            }`}
          >
            {isRowUpdating && (
              <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
            )}
            {!isRowUpdating && (
              <input
                type="checkbox"
                className="border-gray-300 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                checked={row.getIsSelected()}
                onChange={(e) => {
                  e.stopPropagation();
                  row.toggleSelected(e.target.checked);
                }}
                disabled={Boolean(updatingIds.size > 0) || isRowUpdating}
              />
            )}
          </div>
        );
      },
      enableSorting: false,
      enableHiding: false,
      size: 50,
      minSize: 50,
      maxSize: 50,
    },

    {
      accessorKey: "username",
      header: () => <div className="text-center">{t.username}</div>,
      size: 140,
      minSize: 120,
      maxSize: 180,
      cell: (info) => {
        const isRowUpdating = Boolean(
          info.row.original.id && updatingIds.has(info.row.original.id)
        );
        return (
          <div
            className={`flex items-center justify-center gap-2 ${
              isRowUpdating ? "opacity-60 pointer-events-none" : ""
            }`}
          >
            <UserIcon className="w-4 h-4 text-gray-600" />
            <span className="font-medium">{info.getValue() as string}</span>
          </div>
        );
      },
    },

    {
      accessorKey: "fullName",
      header: () => <div className="text-center">{t.fullName}</div>,
      size: 160,
      minSize: 140,
      maxSize: 250,
      cell: (info) => {
        const isRowUpdating = Boolean(
          info.row.original.id && updatingIds.has(info.row.original.id)
        );
        return (
          <div
            className={`text-center ${
              isRowUpdating ? "opacity-60 pointer-events-none" : ""
            }`}
          >
            {String(info.getValue() || "—")}
          </div>
        );
      },
    },

    {
      accessorKey: "email",
      header: () => <div className="text-center">{t.email}</div>,
      size: 80,
      minSize: 80,
      maxSize: 250,
      cell: (info) => {
        const isRowUpdating = Boolean(
          info.row.original.id && updatingIds.has(info.row.original.id)
        );
        return (
          <div
            className={`text-center ${
              isRowUpdating ? "opacity-60 pointer-events-none" : ""
            }`}
          >
            {String(info.getValue() || "—")}
          </div>
        );
      },
    },

    {
      accessorKey: "title",
      header: () => <div className="text-center">{t.title}</div>,
      size: 80,
      minSize: 80,
      maxSize: 200,
      cell: (info) => {
        const isRowUpdating = Boolean(
          info.row.original.id && updatingIds.has(info.row.original.id)
        );
        return (
          <div
            className={`text-center ${
              isRowUpdating ? "opacity-60 pointer-events-none" : ""
            }`}
          >
            {String(info.getValue() || "—")}
          </div>
        );
      },
    },

    {
      id: "userSource",
      accessorKey: "userSource",
      header: () => <div className="text-center">{t.source}</div>,
      cell: ({ row }) => {
        const user = row.original;
        const isRowUpdating = Boolean(user.id && updatingIds.has(user.id));
        return (
          <div
            className={`flex justify-center ${
              isRowUpdating ? "opacity-60 pointer-events-none" : ""
            }`}
          >
            <UserSourceBadge
              userSource={user.userSource}
              userSourceMetadata={user.userSourceMetadata}
              language={language}
            />
          </div>
        );
      },
      size: 90,
      minSize: 85,
      maxSize: 110,
    },

    {
      id: "statusOverride",
      accessorKey: "statusOverride",
      header: () => <div className="text-center">{t.override}</div>,
      cell: ({ row }) => {
        const user = row.original;
        const isRowUpdating = Boolean(user.id && updatingIds.has(user.id));
        return (
          <div
            className={`flex justify-center ${
              isRowUpdating ? "opacity-60 pointer-events-none" : ""
            }`}
          >
            <UserOverrideIndicator user={user} language={language} />
          </div>
        );
      },
      size: 90,
      minSize: 85,
      maxSize: 110,
    },

    {
      id: "isActive",
      accessorKey: "isActive",
      header: () => <div className="text-center">{t.active}</div>,
      cell: ({ row }) => {
        const user = row.original;
        const isRowUpdating = Boolean(user.id && updatingIds.has(user.id));
        return (
          <div
            className={`flex justify-center items-center ${
              isRowUpdating ? "opacity-60 pointer-events-none" : ""
            }`}
          >
            <StatusSwitch
              checked={user.isActive}
              onToggle={async () => {
                if (!user.id) return;
                const newStatus = !user.isActive;
                markUpdating([user.id]);
                try {
                  // Call API and wait for server response
                  const result = await toggleUserStatus(user.id, newStatus);

                  // Update UI only after successful server response
                  await updateUsers([result]);

                  // Show success toast
                  const successMsg = newStatus ? t.activateSuccess : t.deactivateSuccess;
                  toast.success(successMsg);
                  clearUpdating([user.id]);
                } catch (error) {
                  console.error("Failed to toggle user status:", error);
                  clearUpdating([user.id]);
                  throw error;
                }
              }}
              title={user.isActive ? t.deactivateUser : t.activateUser}
              description={
                user.isActive
                  ? t.deactivateMessage.replace('{username}', user.username)
                  : t.activateMessage.replace('{username}', user.username)
              }
              size="sm"
            />
          </div>
        );
      },
      enableHiding: true,
      size: 50,
      minSize: 50,
      maxSize: 50,
    },

    {
      id: "isBlocked",
      accessorKey: "isBlocked",
      header: () => <div className="text-center">{t.blocked}</div>,
      cell: ({ row }) => {
        const user = row.original;
        const isRowUpdating = Boolean(user.id && updatingIds.has(user.id));
        return (
          <div
            className={`flex justify-center items-center ${
              isRowUpdating ? "opacity-60 pointer-events-none" : ""
            }`}
          >
            <StatusSwitch
              checked={user.isBlocked}
              onToggle={async () => {
                if (!user.id) return;
                const newBlockedStatus = !user.isBlocked;
                markUpdating([user.id]);
                try {
                  // Call API and wait for server response
                  const result = await toggleUserBlock(user.id, newBlockedStatus);

                  // Update UI only after successful server response
                  await updateUsers([result]);

                  // Show success toast
                  const successMsg = newBlockedStatus ? t.blockSuccess : t.unblockSuccess;
                  toast.success(successMsg);
                  clearUpdating([user.id]);
                } catch (error) {
                  console.error("Failed to toggle user block status:", error);
                  clearUpdating([user.id]);
                  throw error;
                }
              }}
              title={user.isBlocked ? t.unblockUser : t.blockUser}
              description={
                user.isBlocked
                  ? t.unblockMessage.replace('{username}', user.username)
                  : t.blockMessage.replace('{username}', user.username)
              }
              size="sm"
            />
          </div>
        );
      },
      enableHiding: true,
      size: 50,
      minSize: 50,
      maxSize: 50,
    },

    {
      id: "roles",
      header: () => <div className="text-center">{t.roles}</div>,
      accessorFn: (row) => row.roleIds?.join(", ") || "",
      size: 120,
      minSize: 100,
      maxSize: 200,
      cell: ({ row }) => {
        const isRowUpdating = Boolean(
          row.original.id && updatingIds.has(row.original.id)
        );
        const userRoleIds = row.original.roleIds || [];

        if (!userRoleIds || userRoleIds.length === 0) {
          return (
            <div
              className={`flex justify-center ${
                isRowUpdating ? "opacity-60 pointer-events-none" : ""
              }`}
            >
              <Badge variant="secondary" className="text-xs">
                {t.noRoles}
              </Badge>
            </div>
          );
        }

        return (
          <div
            className={`flex flex-wrap gap-1 justify-center ${
              isRowUpdating ? "opacity-60 pointer-events-none" : ""
            }`}
          >
            {userRoleIds.map((roleId, index) => (
              <Badge key={index} variant="outline" className="text-xs">
                {getRoleDisplayName(roleId, roleOptions, language)}
              </Badge>
            ))}
          </div>
        );
      },
    },

    {
      id: "departments",
      header: () => <div className="text-center">{t.departments}</div>,
      accessorFn: (row) => row.assignedDepartmentCount ?? 0,
      cell: ({ row }) => {
        const isRowUpdating = Boolean(
          row.original.id && updatingIds.has(row.original.id)
        );
        const count = row.original.assignedDepartmentCount;

        // If count is 0, null, or undefined, user has access to ALL departments
        const isAllDepartments = count === undefined || count === null || count === 0;

        return (
          <div
            className={`flex items-center justify-center gap-1.5 ${
              isRowUpdating ? "opacity-60 pointer-events-none" : ""
            }`}
          >
            <Building2 className="h-3.5 w-3.5 text-muted-foreground" />
            {isAllDepartments ? (
              <Badge variant="secondary" className="text-xs bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300">
                {t.allDepartments}
              </Badge>
            ) : (
              <span className="text-sm font-medium">{count}</span>
            )}
          </div>
        );
      },
      size: 110,
      minSize: 100,
      maxSize: 140,
    },

    {
      id: "actions",
      header: () => <div className="text-center pe-4">{t.actions}</div>,
      cell: ({ row }) => {
        const isRowUpdating = Boolean(
          row.original.id && updatingIds.has(row.original.id)
        );
        return (
          <div
            className={`flex justify-center pe-4 ${
              isRowUpdating ? "opacity-60 pointer-events-none" : ""
            }`}
            onClick={(e) => e.stopPropagation()}
          >
            {/* This will be populated in the body component */}
          </div>
        );
      },
      enableSorting: false,
      enableHiding: false,
      size: 180,
      minSize: 180,
      maxSize: 180,
    },
  ];
}
