"use client";

import { createContext, useContext, ReactNode } from "react";
import type {
  UserWithRolesResponse,
  RoleResponse,
  AuthUserResponse,
} from "@/types/users";
import type { DepartmentForAssignment } from "@/lib/actions/departments.actions";

interface UsersActionsContextType {
  onToggleUserStatus: (
    userId: string,
    isActive: boolean
  ) => Promise<{
    success: boolean;
    message?: string;
    error?: string;
  }>;
  onUpdateUser: (
    userId: string,
    updatedUser: {
      fullname?: string | null;
      title?: string | null;
      roleIds: number[];
    }
  ) => Promise<{
    success: boolean;
    message?: string;
    data?: UserWithRolesResponse;
    error?: string;
  }>;
  updateUsers: (updatedUsers: UserWithRolesResponse[]) => Promise<void>;
  onBulkUpdateStatus: (
    userIds: string[],
    isActive: boolean
  ) => Promise<{
    success: boolean;
    message?: string;
    data?: UserWithRolesResponse[];
    error?: string;
  }>;
  onRefreshUsers: () => Promise<{
    success: boolean;
    message?: string;
    data?: null;
  }>;
}

interface UsersDataContextType {
  roles: RoleResponse[];
  domainUsers: AuthUserResponse[];
  departments: DepartmentForAssignment[];
}

type UsersContextType = UsersActionsContextType & UsersDataContextType;

const UsersContext = createContext<UsersContextType | null>(null);

interface UsersProviderProps {
  children: ReactNode;
  actions: UsersActionsContextType;
  roles: RoleResponse[];
  departments: DepartmentForAssignment[];
  domainUsers?: AuthUserResponse[];
}

export function UsersProvider({
  children,
  actions,
  roles,
  departments,
  domainUsers = [],
}: UsersProviderProps) {
  const value: UsersContextType = {
    ...actions,
    roles,
    departments,
    domainUsers,
  };

  return (
    <UsersContext.Provider value={value}>{children}</UsersContext.Provider>
  );
}

export function useUsersContext() {
  const context = useContext(UsersContext);
  if (!context) {
    throw new Error("useUsersContext must be used within UsersProvider");
  }
  return context;
}

// Convenience hooks for specific data
export function useRoles() {
  const { roles } = useUsersContext();
  return roles;
}

export function useDomainUsers() {
  const { domainUsers } = useUsersContext();
  return domainUsers;
}

export function useDepartments() {
  const { departments } = useUsersContext();
  return departments;
}

export function useUsersActions() {
  const {
    onToggleUserStatus,
    onUpdateUser,
    updateUsers,
    onBulkUpdateStatus,
    onRefreshUsers,
  } = useUsersContext();
  return {
    onToggleUserStatus,
    onUpdateUser,
    updateUsers,
    onBulkUpdateStatus,
    onRefreshUsers,
  };
}
