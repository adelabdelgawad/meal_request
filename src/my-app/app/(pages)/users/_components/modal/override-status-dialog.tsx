"use client";

import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { AlertCircle, Shield, ShieldOff } from "lucide-react";
import { toast } from "@/components/ui/custom-toast";
import { overrideUserStatus } from "@/lib/api/users";
import type { UserWithRolesResponse } from "@/types/users";

interface OverrideStatusDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user: UserWithRolesResponse;
  action: "enable" | "disable";
  onSuccess: (updatedUser: UserWithRolesResponse) => void;
  language: string;
}

/**
 * Dialog for enabling or disabling status override for a user
 * Enable: Optional reason field
 * Disable: Confirmation only
 */
export function OverrideStatusDialog({
  open,
  onOpenChange,
  user,
  action,
  onSuccess,
  language,
}: OverrideStatusDialogProps) {
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isEnabling = action === "enable";
  const isArabic = language === "ar";

  const handleSubmit = async () => {
    setIsSubmitting(true);

    try {
      const response = await overrideUserStatus(user.id, {
        statusOverride: isEnabling,
        overrideReason: isEnabling && reason.trim() ? reason.trim() : null,
      });

      toast.success(
        isArabic
          ? response.message || "تم تحديث التجاوز بنجاح"
          : response.message || "Override updated successfully"
      );

      onSuccess(response.user);
      onOpenChange(false);
      setReason(""); // Reset reason
    } catch (error) {
      console.error("Failed to update override:", error);
      toast.error(
        isArabic
          ? "فشل في تحديث التجاوز"
          : "Failed to update override"
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    setReason(""); // Reset reason
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <div className="flex items-center gap-2">
            {isEnabling ? (
              <Shield className="w-5 h-5 text-amber-600" />
            ) : (
              <ShieldOff className="w-5 h-5 text-gray-600" />
            )}
            <DialogTitle>
              {isEnabling
                ? isArabic
                  ? "تفعيل تجاوز الحالة"
                  : "Enable Status Override"
                : isArabic
                ? "إيقاف تجاوز الحالة"
                : "Disable Status Override"}
            </DialogTitle>
          </div>
          <DialogDescription>
            {isEnabling
              ? isArabic
                ? `تفعيل التجاوز للمستخدم: ${user.username}`
                : `Enable override for user: ${user.username}`
              : isArabic
              ? `إيقاف التجاوز للمستخدم: ${user.username}`
              : `Disable override for user: ${user.username}`}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Info Box */}
          <div className="flex items-start gap-2 p-3 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-md">
            <AlertCircle className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-800 dark:text-blue-200">
              {isEnabling ? (
                <>
                  {isArabic ? (
                    <>
                      <p className="font-medium mb-1">ماذا يعني هذا؟</p>
                      <p>
                        عند تفعيل التجاوز، لن تقوم مزامنة HRIS بتغيير حالة هذا المستخدم
                        (نشط/غير نشط). ستتمكن من التحكم في حالة المستخدم يدويًا بغض النظر عن
                        بيانات HRIS.
                      </p>
                    </>
                  ) : (
                    <>
                      <p className="font-medium mb-1">What does this mean?</p>
                      <p>
                        When override is enabled, HRIS sync will not modify this user's
                        active/inactive status. You will be able to control the user's status
                        manually regardless of HRIS data.
                      </p>
                    </>
                  )}
                </>
              ) : (
                <>
                  {isArabic ? (
                    <>
                      <p className="font-medium mb-1">ماذا يعني هذا؟</p>
                      <p>
                        عند إيقاف التجاوز، ستعود مزامنة HRIS لإدارة حالة هذا المستخدم
                        تلقائيًا بناءً على بيانات HRIS.
                      </p>
                    </>
                  ) : (
                    <>
                      <p className="font-medium mb-1">What does this mean?</p>
                      <p>
                        When override is disabled, HRIS sync will resume automatically
                        managing this user's status based on HRIS data.
                      </p>
                    </>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Reason Input (only for enable) */}
          {isEnabling && (
            <div className="space-y-2">
              <Label htmlFor="override-reason">
                {isArabic ? "السبب (اختياري)" : "Reason (Optional)"}
              </Label>
              <Textarea
                id="override-reason"
                placeholder={
                  isArabic
                    ? "اشرح سبب تفعيل التجاوز (اختياري)"
                    : "Explain why you are enabling override (optional)"
                }
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={4}
                maxLength={500}
                className="resize-none"
              />
              <p className="text-xs text-muted-foreground">
                {isArabic
                  ? "يمكنك تقديم تفسير لماذا يحتاج هذا المستخدم إلى استثناء"
                  : "You can provide an explanation for why this user needs an override"}
              </p>
            </div>
          )}

          {/* Current Override Info (for disable) */}
          {!isEnabling && user.overrideReason && (
            <div className="space-y-2">
              <Label>{isArabic ? "السبب الحالي" : "Current Reason"}</Label>
              <div className="p-3 bg-gray-50 dark:bg-gray-900 border rounded-md text-sm">
                {user.overrideReason}
              </div>
              {user.overrideSetAt && (
                <p className="text-xs text-muted-foreground">
                  {isArabic ? "تم التعيين في:" : "Set on:"}{" "}
                  {new Date(user.overrideSetAt).toLocaleDateString(
                    isArabic ? "ar-SA" : "en-US",
                    {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    }
                  )}
                </p>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleCancel}
            disabled={isSubmitting}
          >
            {isArabic ? "إلغاء" : "Cancel"}
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting}
          >
            {isSubmitting
              ? isArabic
                ? "جاري الحفظ..."
                : "Saving..."
              : isEnabling
              ? isArabic
                ? "تفعيل التجاوز"
                : "Enable Override"
              : isArabic
              ? "إيقاف التجاوز"
              : "Disable Override"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
