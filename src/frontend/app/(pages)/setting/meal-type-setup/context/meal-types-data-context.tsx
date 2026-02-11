"use client";

import { createContext, useContext, useState, ReactNode } from "react";
import type { MealTypeResponse } from "@/types/meal-types";

interface MealTypesDataContextType {
  selectedMealType: MealTypeResponse | null;
  setSelectedMealType: (mealType: MealTypeResponse | null) => void;
  isModalOpen: boolean;
  setIsModalOpen: (isOpen: boolean) => void;
  modalMode: "create" | "edit";
  setModalMode: (mode: "create" | "edit") => void;
}

const MealTypesDataContext = createContext<MealTypesDataContextType | undefined>(undefined);

export function MealTypesDataProvider({ children }: { children: ReactNode }) {
  const [selectedMealType, setSelectedMealType] = useState<MealTypeResponse | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<"create" | "edit">("create");

  return (
    <MealTypesDataContext.Provider
      value={{
        selectedMealType,
        setSelectedMealType,
        isModalOpen,
        setIsModalOpen,
        modalMode,
        setModalMode,
      }}
    >
      {children}
    </MealTypesDataContext.Provider>
  );
}

export function useMealTypesData() {
  const context = useContext(MealTypesDataContext);
  if (context === undefined) {
    throw new Error("useMealTypesData must be used within MealTypesDataProvider");
  }
  return context;
}
