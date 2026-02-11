"use client";

import { Button } from "@/components/ui/button";
import {
  Edit,
  Eye,
  Building2,
  Shield,
  ShieldOff,
} from "lucide-react";
import { useState } from "react";
import { EditUserSheet } from "../modal/edit-user-sheet";
import { ViewUserSheet } from "../modal/view-user-sheet";
import { DepartmentAssignmentSheet } from "../modal/department-assignment-sheet";
import { OverrideStatusDialog } from "../modal/override-status-dialog";
import type { UserWithRolesResponse } from "@/types/users";
import { useDepartments } from "../../context/users-actions-context";
import { useLanguage } from "@/hooks/use-language";

interface UserActionsProps {
  user: UserWithRolesResponse;
  onUpdate: () => void;
  onUserUpdated?: (updatedUser: UserWithRolesResponse) => void;
  disabled?: boolean;
}

export function UserActions({ user, onUpdate, onUserUpdated, disabled = false }: UserActionsProps) {
  const departments = useDepartments();
  const { language } = useLanguage();
  const [editingUser, setEditingUser] = useState<UserWithRolesResponse | null>(
    null
  );
  const [viewingUser, setViewingUser] = useState<UserWithRolesResponse | null>(
    null
  );
  const [departmentUser, setDepartmentUser] = useState<UserWithRolesResponse | null>(
    null
  );
  const [overrideDialogUser, setOverrideDialogUser] = useState<{
    user: UserWithRolesResponse;
    action: "enable" | "disable";
  } | null>(null);

  const handleViewUser = () => {
    setViewingUser(user);
  };

  const handleEditUser = () => {
    setEditingUser(user);
  };

  const handleDepartments = () => {
    setDepartmentUser(user);
  };

  const handleEnableOverride = () => {
    setOverrideDialogUser({ user, action: "enable" });
  };

  const handleDisableOverride = () => {
    setOverrideDialogUser({ user, action: "disable" });
  };

  // Check if user can have override (only HRIS users)
  const canOverride = user.userSource === "hris";
  const hasOverride = user.statusOverride;

  return (
    <>
      <div className="flex items-center gap-1">
        {/* View User Button */}
        <Button
          variant="ghost"
          size="sm"
          className="h-9 w-9 p-0"
          onClick={(e) => {
            e.stopPropagation();
            handleViewUser();
          }}
          disabled={disabled}
        >
          <span className="sr-only">View User</span>
          <Eye className="h-4 w-4 text-blue-600" />
        </Button>

        {/* Edit User Button */}
        <Button
          variant="ghost"
          size="sm"
          className="h-9 w-9 p-0"
          onClick={(e) => {
            e.stopPropagation();
            handleEditUser();
          }}
          disabled={disabled}
        >
          <span className="sr-only">Edit User</span>
          <Edit className="h-4 w-4 text-gray-600" />
        </Button>

        {/* Department Assignments Button */}
        <Button
          variant="ghost"
          size="sm"
          className="h-9 w-9 p-0"
          onClick={(e) => {
            e.stopPropagation();
            handleDepartments();
          }}
          disabled={disabled}
        >
          <span className="sr-only">Department Assignments</span>
          <Building2 className="h-4 w-4 text-purple-600" />
        </Button>

        {/* Override Status Button (only for HRIS users) */}
        {canOverride && (
          <Button
            variant="ghost"
            size="sm"
            className="h-9 w-9 p-0"
            onClick={(e) => {
              e.stopPropagation();
              if (hasOverride) {
                handleDisableOverride();
              } else {
                handleEnableOverride();
              }
            }}
            disabled={disabled}
            title={
              hasOverride
                ? language === "ar"
                  ? "إيقاف تجاوز الحالة"
                  : "Disable Status Override"
                : language === "ar"
                ? "تفعيل تجاوز الحالة"
                : "Enable Status Override"
            }
          >
            <span className="sr-only">
              {hasOverride ? "Disable Override" : "Enable Override"}
            </span>
            {hasOverride ? (
              <ShieldOff className="h-4 w-4 text-gray-600" />
            ) : (
              <Shield className="h-4 w-4 text-amber-600" />
            )}
          </Button>
        )}
      </div>

      {/* Sheets */}
      {editingUser && (
        <EditUserSheet
          open={true}
          onOpenChange={(open) => {
            if (!open) {
              setEditingUser(null);
            }
          }}
          user={editingUser}
          onSuccess={() => {
            onUpdate();
            setEditingUser(null);
          }}
          onUserUpdated={(updatedUser) => {
            // Update the specific user in the table without full refetch
            if (onUserUpdated) {
              onUserUpdated(updatedUser);
              // No need to call onUpdate() - updateUsers already updates the SWR cache
            } else {
              // Fallback to full refetch if no optimized handler provided
              onUpdate();
            }
            setEditingUser(null);
          }}
        />
      )}

      {viewingUser && (
        <ViewUserSheet
          open={true}
          onOpenChange={(open) => {
            if (!open) {
              setViewingUser(null);
            }
          }}
          user={viewingUser}
        />
      )}

      {departmentUser && (
        <DepartmentAssignmentSheet
          open={true}
          onOpenChange={(open) => {
            if (!open) {
              setDepartmentUser(null);
            }
          }}
          user={departmentUser}
          departments={departments}
          onSuccess={() => {
            onUpdate();
            setDepartmentUser(null);
          }}
        />
      )}

      {/* Override Status Dialog */}
      {overrideDialogUser && (
        <OverrideStatusDialog
          open={true}
          onOpenChange={(open) => {
            if (!open) {
              setOverrideDialogUser(null);
            }
          }}
          user={overrideDialogUser.user}
          action={overrideDialogUser.action}
          onSuccess={(updatedUser) => {
            // Update the specific user in the table
            if (onUserUpdated) {
              onUserUpdated(updatedUser);
            } else {
              // Fallback to full refetch
              onUpdate();
            }
            setOverrideDialogUser(null);
          }}
          language={language}
        />
      )}
    </>
  );
}
