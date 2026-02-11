"use client";

import { toast } from "@/components/ui/custom-toast";
import { updateUsersStatus } from "@/lib/api/users";
import type { UserWithRolesResponse } from "@/types/users";

interface ToastTranslations {
  enabledMultiple: string;
  disabledMultiple: string;
  alreadyEnabled: string;
  alreadyDisabled: string;
  enableError: string;
  disableError: string;
}

interface UsersTableActionsProps {
  users: UserWithRolesResponse[];
  updateUsers: (updatedUsers: UserWithRolesResponse[]) => Promise<void>;
  markUpdating: (ids: string[]) => void;
  clearUpdating: (ids?: string[]) => void;
  toastMessages?: ToastTranslations;
}

// Default messages (fallback when translations not provided)
const defaultMessages: ToastTranslations = {
  enabledMultiple: "Successfully enabled {count} user(s)",
  disabledMultiple: "Successfully disabled {count} user(s)",
  alreadyEnabled: "Selected users are already enabled",
  alreadyDisabled: "Selected users are already disabled",
  enableError: "Failed to enable users",
  disableError: "Failed to disable users",
};

/**
 * Handles bulk action operations for users
 */
export function useUsersTableActions({
  users,
  updateUsers,
  markUpdating,
  clearUpdating,
  toastMessages,
}: UsersTableActionsProps) {
  const messages = toastMessages || defaultMessages;

  // Handle disable users
  const handleDisable = async (ids: string[]) => {
    try {
      if (ids.length === 0) {return;}

      // Filter to only active users (ones that need to be disabled)
      const activeUsersToDisable = users.filter(
        u => u.id && ids.includes(u.id) && u.isActive
      );

      if (activeUsersToDisable.length === 0) {
        toast.info(messages.alreadyDisabled);
        return;
      }

      const userIdsToDisable = activeUsersToDisable.map(u => u.id!);

      // Mark users as updating (show loading spinner)
      markUpdating(userIdsToDisable);

      // Call API and get updated users
      const response = await updateUsersStatus(userIdsToDisable, false);

      // Update local state with returned _data
      if (response.updatedUsers && response.updatedUsers.length > 0) {
        updateUsers(response.updatedUsers);

        // Wait for state to update before clearing loading spinner
        // This ensures spinner stays visible until UI actually updates
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      // Show success toast with localized message
      const successMsg = messages.disabledMultiple.replace("{count}", String(response.updatedUsers.length));
      toast.success(successMsg);

      // Keep selection for further actions
    } catch (error: unknown) {
      // Log technical error to console only
      console.error("Failed to disable users:", error);
      // Show user-friendly error message
      toast.error(messages.disableError);
    } finally {
      // Clear updating state (after UI has updated)
      clearUpdating();
    }
  };

  // Handle enable users
  const handleEnable = async (ids: string[]) => {
    try {
      if (ids.length === 0) {return;}

      // Filter to only inactive users (ones that need to be enabled)
      const inactiveUsersToEnable = users.filter(
        u => u.id && ids.includes(u.id) && !u.isActive
      );

      if (inactiveUsersToEnable.length === 0) {
        toast.info(messages.alreadyEnabled);
        return;
      }

      const userIdsToEnable = inactiveUsersToEnable.map(u => u.id!);

      // Mark users as updating (show loading spinner)
      markUpdating(userIdsToEnable);

      // Call API and get updated users
      const response = await updateUsersStatus(userIdsToEnable, true);

      // Update local state with returned _data
      if (response.updatedUsers && response.updatedUsers.length > 0) {
        updateUsers(response.updatedUsers);

        // Wait for state to update before clearing loading spinner
        // This ensures spinner stays visible until UI actually updates
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      // Show success toast with localized message
      const successMsg = messages.enabledMultiple.replace("{count}", String(response.updatedUsers.length));
      toast.success(successMsg);

      // Keep selection for further actions
    } catch (error: unknown) {
      // Log technical error to console only
      console.error("Failed to enable users:", error);
      // Show user-friendly error message
      toast.error(messages.enableError);
    } finally {
      // Clear updating state (after UI has updated)
      clearUpdating();
    }
  };

  return {
    handleDisable,
    handleEnable,
  };
}
