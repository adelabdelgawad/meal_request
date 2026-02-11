"use client";

import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Loader2 } from "lucide-react";
import { useMealTypesData } from "../../context/meal-types-data-context";
import { useLanguage, translate } from "@/hooks/use-language";
import { createMealType, updateMealType } from "@/lib/actions/meal-types.actions";
import { toast } from "sonner";
import type { MealTypeResponse } from "@/types/meal-types";

interface MealTypeModalProps {
  addMealType: (mealType: MealTypeResponse) => Promise<void>;
  updateMealTypes: (mealTypes: MealTypeResponse[]) => Promise<void>;
}

export function MealTypeModal({ addMealType, updateMealTypes }: MealTypeModalProps) {
  const { selectedMealType, isModalOpen, setIsModalOpen, modalMode } = useMealTypesData();
  const { t } = useLanguage();

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    nameEn: "",
    nameAr: "",
    priority: 0,
    isActive: true,
  });

  // Reset form when modal opens/closes or meal type changes
  useEffect(() => {
    if (isModalOpen && selectedMealType && modalMode === "edit") {
      setFormData({
        nameEn: selectedMealType.nameEn,
        nameAr: selectedMealType.nameAr,
        priority: selectedMealType.priority,
        isActive: selectedMealType.isActive,
      });
    } else if (isModalOpen && modalMode === "create") {
      setFormData({
        nameEn: "",
        nameAr: "",
        priority: 0,
        isActive: true,
      });
    }
  }, [isModalOpen, selectedMealType, modalMode]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      if (modalMode === "create") {
        const result = await createMealType({
          nameEn: formData.nameEn,
          nameAr: formData.nameAr,
          priority: formData.priority,
        });

        if (result.success && result.data) {
          await addMealType(result.data);
          toast.success(translate(t, "mealTypes.messages.createSuccess") || "Meal type created successfully");
          setIsModalOpen(false);
        } else {
          toast.error(result.error || translate(t, "mealTypes.messages.createError") || "Failed to create meal type");
        }
      } else if (selectedMealType) {
        const result = await updateMealType(selectedMealType.id, {
          nameEn: formData.nameEn,
          nameAr: formData.nameAr,
          priority: formData.priority,
          isActive: formData.isActive,
        });

        if (result.success && result.data) {
          await updateMealTypes([result.data]);
          toast.success(translate(t, "mealTypes.messages.updateSuccess") || "Meal type updated successfully");
          setIsModalOpen(false);
        } else {
          toast.error(result.error || translate(t, "mealTypes.messages.updateError") || "Failed to update meal type");
        }
      }
    } catch (error) {
      console.error("Error submitting meal type:", error);
      toast.error(translate(t, "mealTypes.messages.createError") || "An error occurred");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setIsModalOpen(false);
    }
  };

  return (
    <Dialog open={isModalOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>
            {modalMode === "create"
              ? translate(t, "mealTypes.form.createTitle") || "Create New Meal Type"
              : translate(t, "mealTypes.form.editTitle") || "Edit Meal Type"}
          </DialogTitle>
          <DialogDescription>
            {modalMode === "create"
              ? "Add a new meal type to the system"
              : "Update the meal type information"}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* English Name */}
          <div className="space-y-2">
            <Label htmlFor="nameEn">
              {translate(t, "mealTypes.form.nameEn") || "English Name"}
            </Label>
            <Input
              id="nameEn"
              value={formData.nameEn}
              onChange={(e) => setFormData({ ...formData, nameEn: e.target.value })}
              placeholder={translate(t, "mealTypes.form.nameEnPlaceholder") || "Enter English name"}
              required
              disabled={isSubmitting}
            />
          </div>

          {/* Arabic Name */}
          <div className="space-y-2">
            <Label htmlFor="nameAr">
              {translate(t, "mealTypes.form.nameAr") || "Arabic Name"}
            </Label>
            <Input
              id="nameAr"
              value={formData.nameAr}
              onChange={(e) => setFormData({ ...formData, nameAr: e.target.value })}
              placeholder={translate(t, "mealTypes.form.nameArPlaceholder") || "Enter Arabic name"}
              required
              disabled={isSubmitting}
              dir="rtl"
            />
          </div>

          {/* Priority */}
          <div className="space-y-2">
            <Label htmlFor="priority">
              {translate(t, "mealTypes.form.priority") || "Priority"}
            </Label>
            <Input
              id="priority"
              type="number"
              value={formData.priority}
              onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })}
              placeholder={translate(t, "mealTypes.form.priorityPlaceholder") || "Enter priority"}
              min={0}
              disabled={isSubmitting}
            />
            <p className="text-xs text-muted-foreground">
              {translate(t, "mealTypes.form.priorityHelper") || "Higher priority meal types are selected by default"}
            </p>
          </div>

          {/* Active Toggle (only for edit mode) */}
          {modalMode === "edit" && (
            <div className="flex items-center justify-between rounded-lg border p-4">
              <div className="space-y-0.5">
                <Label htmlFor="isActive">
                  {translate(t, "mealTypes.form.isActive") || "Active"}
                </Label>
                <p className="text-xs text-muted-foreground">
                  Inactive meal types will not appear in the meal request form
                </p>
              </div>
              <Switch
                id="isActive"
                checked={formData.isActive}
                onCheckedChange={(checked) => setFormData({ ...formData, isActive: checked })}
                disabled={isSubmitting}
              />
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isSubmitting}
              className="flex-1"
            >
              {translate(t, "mealTypes.form.cancel") || "Cancel"}
            </Button>
            <Button type="submit" disabled={isSubmitting} className="flex-1 gap-2">
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {translate(t, "mealTypes.form.submit") || "Save"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
