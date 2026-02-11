"use client";

import { Button } from "@/components/ui/button";
import {
  Edit,
  Shield,
  Users,
} from "lucide-react";
import { useState } from "react";
import { useLanguage } from "@/hooks/use-language";
import { EditRolePagesSheet } from "../modal/edit-role-pages-sheet";
import { EditRoleSheet } from "../modal/edit-role-sheet";
import { EditRoleUsersSheet } from "../modal/edit-role-users-sheet";
import { useRolesActions } from "@/app/(pages)/setting/roles/context/roles-actions-context";
import { useRolesData } from "@/app/(pages)/setting/roles/context/roles-data-context";
import type { RoleResponse } from "@/types/roles";

interface RoleActionsProps {
  role: RoleResponse;
}

export function RoleActions({ role }: RoleActionsProps) {
  const { t } = useLanguage();
  const settingRoles = (t as Record<string, unknown>).settingRoles as Record<string, unknown> | undefined;
  const actions = (settingRoles?.actions as Record<string, string>) || {};

  const { pages, users } = useRolesData();
  const { handleUpdateRole, updateCounts } = useRolesActions();
  const [editRolesOpen, setEditRolesOpen] = useState(false);
  const [editRoleOpen, setEditRoleOpen] = useState(false);
  const [editUsersOpen, setEditUsersOpen] = useState(false);

  return (
    <>
      <div className="flex items-center gap-1">
        {/* Edit Role Button */}
        <Button
          variant="ghost"
          size="sm"
          className="h-9 w-9 p-0"
          onClick={(e) => {
            e.stopPropagation();
            setEditRoleOpen(true);
          }}
        >
          <span className="sr-only">{actions.editRole || "Edit Role"}</span>
          <Edit className="h-4 w-4 text-gray-600" />
        </Button>

        {/* Edit Pages Button */}
        <Button
          variant="ghost"
          size="sm"
          className="h-9 w-9 p-0"
          onClick={(e) => {
            e.stopPropagation();
            setEditRolesOpen(true);
          }}
        >
          <span className="sr-only">{actions.editPages || "Edit Pages"}</span>
          <Shield className="h-4 w-4 text-blue-600" />
        </Button>

        {/* Edit Users Button */}
        <Button
          variant="ghost"
          size="sm"
          className="h-9 w-9 p-0"
          onClick={(e) => {
            e.stopPropagation();
            setEditUsersOpen(true);
          }}
        >
          <span className="sr-only">{actions.editUsers || "Edit Users"}</span>
          <Users className="h-4 w-4 text-purple-600" />
        </Button>
      </div>

      {/* Edit Role Sheet */}
      <EditRoleSheet
        role={role}
        open={editRoleOpen}
        onOpenChange={(open) => {
          setEditRoleOpen(open);
          if (!open) {
            setTimeout(() => {
              (document.activeElement as HTMLElement | null)?.blur();
            }, 100);
          }
        }}
        onUpdate={(updatedRole) => {
          handleUpdateRole(role.id, updatedRole);
        }}
        onMutate={async () => {
          await updateCounts();
        }}
      />

      {/* Edit Pages Sheet */}
      <EditRolePagesSheet
        role={role}
        open={editRolesOpen}
        onOpenChange={(open) => {
          setEditRolesOpen(open);
          if (!open) {
            setTimeout(() => {
              (document.activeElement as HTMLElement | null)?.blur();
            }, 100);
          }
        }}
        onMutate={async () => {
          await updateCounts();
        }}
        preloadedPages={pages}
      />

      {/* Edit Users Sheet */}
      <EditRoleUsersSheet
        role={role}
        open={editUsersOpen}
        onOpenChange={(open) => {
          setEditUsersOpen(open);
          if (!open) {
            setTimeout(() => {
              (document.activeElement as HTMLElement | null)?.blur();
            }, 100);
          }
        }}
        onMutate={async () => {
          await updateCounts();
        }}
        preloadedUsers={users}
      />
    </>
  );
}
