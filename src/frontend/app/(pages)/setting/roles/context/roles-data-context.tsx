"use client";

import { createContext, useContext, type ReactNode } from "react";
import type { PageResponse } from "@/types/pages";
import type { UserResponse } from "@/types/users";

interface RolesDataContextValue {
  pages: PageResponse[];
  users: UserResponse[];
}

const RolesDataContext = createContext<RolesDataContextValue | null>(null);

interface RolesDataProviderProps {
  children: ReactNode;
  pages: PageResponse[];
  users: UserResponse[];
}

export function RolesDataProvider({
  children,
  pages,
  users,
}: RolesDataProviderProps) {
  return (
    <RolesDataContext.Provider value={{ pages, users }}>
      {children}
    </RolesDataContext.Provider>
  );
}

export function useRolesData() {
  const context = useContext(RolesDataContext);
  if (!context) {
    throw new Error("useRolesData must be used within RolesDataProvider");
  }
  return context;
}
