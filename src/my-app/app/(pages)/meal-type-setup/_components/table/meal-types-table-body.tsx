"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Edit, Trash2, Plus, ArrowUpDown, UtensilsCrossed, TrendingUp } from "lucide-react";
import { useMealTypesData } from "../../context/meal-types-data-context";
import { useLanguage, translate } from "@/hooks/use-language";
import { deleteMealType, updateMealType } from "@/lib/actions/meal-types.actions";
import { toast } from "sonner";
import type { MealTypeResponse } from "@/types/meal-types";
import { cn } from "@/lib/utils";

interface MealTypesTableBodyProps {
  mealTypes: MealTypeResponse[];
  updateMealTypes: (mealTypes: MealTypeResponse[]) => Promise<void>;
  removeMealType: (id: number) => Promise<void>;
}

export function MealTypesTableBody({
  mealTypes,
  updateMealTypes,
  removeMealType,
}: MealTypesTableBodyProps) {
  const { setSelectedMealType, setIsModalOpen, setModalMode } = useMealTypesData();
  const { language, t } = useLanguage();
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const handleCreate = () => {
    setSelectedMealType(null);
    setModalMode("create");
    setIsModalOpen(true);
  };

  const handleEdit = (mealType: MealTypeResponse) => {
    setSelectedMealType(mealType);
    setModalMode("edit");
    setIsModalOpen(true);
  };

  const handleToggleActive = async (mealType: MealTypeResponse) => {
    const newStatus = !mealType.isActive;

    try {
      const result = await updateMealType(mealType.id, {
        isActive: newStatus,
      });

      if (result.success && result.data) {
        await updateMealTypes([result.data]);
        toast.success(
          translate(
            t,
            newStatus ? "mealTypes.messages.activateSuccess" : "mealTypes.messages.deactivateSuccess"
          ) || (newStatus ? "Meal type activated" : "Meal type deactivated")
        );
      } else {
        toast.error(result.error || translate(t, "mealTypes.messages.updateError") || "Failed to update");
      }
    } catch (error) {
      console.error("Error toggling meal type:", error);
      toast.error(translate(t, "mealTypes.messages.updateError") || "Failed to update");
    }
  };

  const handleDelete = async (mealType: MealTypeResponse) => {
    if (!confirm(translate(t, "mealTypes.messages.deleteConfirm") || "Are you sure?")) {
      return;
    }

    setDeletingId(mealType.id);

    try {
      const result = await deleteMealType(mealType.id);

      if (result.success) {
        await removeMealType(mealType.id);
        toast.success(translate(t, "mealTypes.messages.deleteSuccess") || "Meal type deleted");
      } else {
        toast.error(result.error || translate(t, "mealTypes.messages.deleteError") || "Failed to delete");
      }
    } catch (error) {
      console.error("Error deleting meal type:", error);
      toast.error(translate(t, "mealTypes.messages.deleteError") || "Failed to delete");
    } finally {
      setDeletingId(null);
    }
  };

  const getLocalizedName = (mealType: MealTypeResponse) => {
    return language === "ar" ? mealType.nameAr : mealType.nameEn;
  };

  const getPriorityColor = (priority: number) => {
    if (priority >= 10) return "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30";
    if (priority >= 5) return "text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-950/30";
    return "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/30";
  };

  return (
    <div className="flex-1 overflow-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {translate(t, "mealTypes.title") || "Meal Type Setup"}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {translate(t, "mealTypes.description") || "Manage meal types for the system"}
          </p>
        </div>
        <Button onClick={handleCreate} className="gap-2">
          <Plus className="h-4 w-4" />
          {translate(t, "mealTypes.actions.create") || "Create Meal Type"}
        </Button>
      </div>

      {/* Meal Types Grid - Operational Design */}
      {mealTypes.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <UtensilsCrossed className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <p className="text-muted-foreground">
              {translate(t, "mealTypes.table.empty") || "No meal types found"}
            </p>
            <Button onClick={handleCreate} variant="outline" className="mt-4 gap-2">
              <Plus className="h-4 w-4" />
              {translate(t, "mealTypes.actions.create") || "Create First Meal Type"}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {mealTypes.map((mealType) => (
            <Card
              key={mealType.id}
              className={cn(
                "relative overflow-hidden transition-all hover:shadow-lg",
                !mealType.isActive && "opacity-60 bg-muted/30"
              )}
            >
              {/* Priority Indicator */}
              <div
                className={cn(
                  "absolute top-0 right-0 px-3 py-1 rounded-bl-lg text-xs font-semibold flex items-center gap-1",
                  getPriorityColor(mealType.priority)
                )}
              >
                <TrendingUp className="h-3 w-3" />
                {mealType.priority}
              </div>

              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <UtensilsCrossed className="h-5 w-5" />
                      {getLocalizedName(mealType)}
                    </CardTitle>
                    <CardDescription className="mt-1">
                      {language === "ar" ? mealType.nameEn : mealType.nameAr}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-3">
                {/* Status Badge */}
                <div className="flex items-center gap-2">
                  <Badge
                    variant={mealType.isActive ? "default" : "secondary"}
                    className={cn(
                      "font-medium",
                      mealType.isActive
                        ? "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-400"
                        : ""
                    )}
                  >
                    {mealType.isActive
                      ? translate(t, "mealTypes.status.active") || "Active"
                      : translate(t, "mealTypes.status.inactive") || "Inactive"}
                  </Badge>
                </div>

                {/* Meta Info */}
                <div className="text-xs text-muted-foreground space-y-1">
                  <div>ID: {mealType.id}</div>
                  <div>
                    {translate(t, "mealTypes.form.priority") || "Priority"}: {mealType.priority}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2 pt-2 border-t">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleEdit(mealType)}
                    className="flex-1 gap-2"
                  >
                    <Edit className="h-3 w-3" />
                    {translate(t, "mealTypes.actions.edit") || "Edit"}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleToggleActive(mealType)}
                    className={cn(
                      "flex-1",
                      mealType.isActive
                        ? "text-orange-600 hover:text-orange-700 hover:bg-orange-50"
                        : "text-green-600 hover:text-green-700 hover:bg-green-50"
                    )}
                  >
                    <ArrowUpDown className="h-3 w-3" />
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleDelete(mealType)}
                    disabled={deletingId === mealType.id}
                    className="text-destructive hover:text-destructive hover:bg-destructive/10"
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
