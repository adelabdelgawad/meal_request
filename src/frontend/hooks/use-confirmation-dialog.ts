'use client';

import { useState, useCallback } from "react";
import { useLanguage, translate } from "@/hooks/use-language";

export interface UseConfirmationDialogReturn {
  isOpen: boolean;
  isLoading: boolean;
  open: () => void;
  close: () => void;
  confirm: () => void;
  setIsLoading: (loading: boolean) => void;
  confirmLabel: string;
  cancelLabel: string;
}

/**
 * Hook to manage confirmation dialog state with i18n support
 * Uses centralized locale system for button labels
 */
export function useConfirmationDialog(
  onConfirm?: () => void | Promise<void>
): UseConfirmationDialogReturn {
  const { t } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const open = useCallback(() => {
    setIsOpen(true);
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
    setIsLoading(false);
  }, []);

  const confirm = useCallback(async () => {
    if (onConfirm) {
      setIsLoading(true);
      try {
        await onConfirm();
      } catch (error) {
        console.error('Confirmation handler error:', error);
      } finally {
        setIsLoading(false);
      }
    }
    close();
  }, [close, onConfirm]);

  return {
    isOpen,
    isLoading,
    open,
    close,
    confirm,
    setIsLoading,
    confirmLabel: translate(t, 'confirmDialog.confirm'),
    cancelLabel: translate(t, 'confirmDialog.cancel'),
  };
}
