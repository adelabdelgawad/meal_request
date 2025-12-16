"use client";

import * as React from "react";
import { Check, X } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useLanguage, translate } from "@/hooks/use-language";

interface StatusSwitchProps {
  checked: boolean;
  onToggle: () => void | Promise<void>;
  title: string;
  description: string;
  disabled?: boolean;
  size?: "sm" | "md" | "lg";
}

export function StatusSwitch({
  checked,
  onToggle,
  title,
  description,
  disabled = false,
  size = "md",
}: StatusSwitchProps) {
  const { t } = useLanguage();
  const [showDialog, setShowDialog] = React.useState(false);
  const [isLoading, setIsLoading] = React.useState(false);

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!disabled) {
      setShowDialog(true);
    }
  };

  const handleConfirm = async () => {
    setIsLoading(true);
    try {
      await onToggle();
      setShowDialog(false);
    } catch (error) {
      console.error("Status toggle failed:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const sizeClasses = {
    sm: "w-8 h-4",
    md: "w-10 h-5",
    lg: "w-12 h-6",
  };

  const iconSizeClasses = {
    sm: "w-2.5 h-2.5",
    md: "w-3 h-3",
    lg: "w-3.5 h-3.5",
  };

  // Get translation class for thumb position
  // LTR: unchecked = left (0), checked = right (positive)
  // RTL: unchecked = right (0), checked = left (positive) - CSS handles RTL via ltr: prefix
  const getTranslateClass = () => {
    if (!checked) return "translate-x-0";

    if (size === "sm") return "translate-x-4";
    if (size === "md") return "translate-x-5";
    return "translate-x-6";
  };

  return (
    <>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={handleClick}
        dir="ltr"
        className={`
          relative inline-flex ${sizeClasses[size]} shrink-0 cursor-pointer rounded-full
          border-2 border-transparent transition-colors duration-200 ease-in-out
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2
          disabled:cursor-not-allowed disabled:opacity-50
          ${checked ? "bg-green-600" : "bg-gray-300"}
        `}
      >
        <span
          className={`
            pointer-events-none inline-block rounded-full bg-white shadow-lg
            ring-0 transition duration-200 ease-in-out flex items-center justify-center
            ${size === "sm" ? "h-3 w-3" : size === "md" ? "h-4 w-4" : "h-5 w-5"}
            ${getTranslateClass()}
          `}
        >
          {checked ? (
            <Check className={`${iconSizeClasses[size]} text-green-600`} />
          ) : (
            <X className={`${iconSizeClasses[size]} text-gray-400`} />
          )}
        </span>
      </button>

      <AlertDialog open={showDialog} onOpenChange={setShowDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{title}</AlertDialogTitle>
            <AlertDialogDescription>{description}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isLoading}>
              {translate(t, 'table.dialog.cancel')}
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirm} disabled={isLoading}>
              {isLoading ? translate(t, 'table.dialog.processing') : translate(t, 'table.dialog.confirm')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
