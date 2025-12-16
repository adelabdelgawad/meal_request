"use client";

import { createContext, useContext, ReactNode } from "react";
import type { RoleResponse } from "@/types/roles";

export interface RolesActionsContextType {
  handleToggleStatus: (roleId: number, newStatus: boolean) => Promise<void>;
  handleUpdateRole: (roleId: number, updatedRole: RoleResponse) => void;
  mutate: () => void;
  updateCounts: () => Promise<void>;
  markUpdating: (ids: number[]) => void;
  clearUpdating: () => void;
  updateRoles: (updatedRoles: RoleResponse[]) => void;
}

// Create context with undefined default
const RolesActionsContext = createContext<RolesActionsContextType | undefined>(
  undefined
);

interface RolesActionsProviderProps {
  children: ReactNode;
  actions: RolesActionsContextType;
}

/**
 * Provider component that makes roles actions available to all child components
 */
export function RolesActionsProvider({
  children,
  actions,
}: RolesActionsProviderProps) {
  return (
    <RolesActionsContext.Provider value={actions}>
      {children}
    </RolesActionsContext.Provider>
  );
}

/**
 * Custom hook to access roles actions from context
 * @throws Error if used outside of RolesActionsProvider
 */
export function useRolesActions() {
  const context = useContext(RolesActionsContext);

  if (context === undefined) {
    throw new Error(
      "useRolesActions must be used within a RolesActionsProvider"
    );
  }

  return context;
}
