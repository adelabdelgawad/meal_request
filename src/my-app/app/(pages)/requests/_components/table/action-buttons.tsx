'use client';

import { Button } from '@/components/ui/button';
import { Eye, Check, X, Loader2 } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { useState } from 'react';
import { useLanguage, translate } from '@/hooks/use-language';

interface ActionButtonsProps {
  requestId: number;
  status: string;
  onView: () => void;
  onApprove: () => Promise<void>;
  onReject: () => Promise<void>;
  isViewLoading?: boolean;
  isActionLoading?: boolean;
}

export function ActionButtons({
  requestId,
  status,
  onView,
  onApprove,
  onReject,
  isViewLoading = false,
  isActionLoading = false,
}: ActionButtonsProps) {
  const [showApproveDialog, setShowApproveDialog] = useState(false);
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { t } = useLanguage();

  const isPending = status.toLowerCase() === 'pending';
  const isDisabled = !isPending || isActionLoading || isLoading;

  const handleApprove = async () => {
    setIsLoading(true);
    try {
      await onApprove();
      setShowApproveDialog(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReject = async () => {
    setIsLoading(true);
    try {
      await onReject();
      setShowRejectDialog(false);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon"
          onClick={onView}
          disabled={isViewLoading}
          className="h-11 w-11 md:h-8 md:w-8 text-blue-500 hover:text-blue-700 hover:bg-blue-50 dark:text-blue-400 dark:hover:text-blue-300 dark:hover:bg-blue-950 disabled:text-muted-foreground disabled:hover:bg-transparent"
        >
          {isViewLoading ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Eye className="h-5 w-5" />
          )}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setShowApproveDialog(true)}
          disabled={isDisabled}
          className="h-11 w-11 md:h-8 md:w-8 text-green-500 hover:text-green-700 hover:bg-green-50 dark:text-green-400 dark:hover:text-green-300 dark:hover:bg-green-950 disabled:text-muted-foreground disabled:hover:bg-transparent"
        >
          {isActionLoading && status.toLowerCase() === 'pending' ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Check className="h-5 w-5" />
          )}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setShowRejectDialog(true)}
          disabled={isDisabled}
          className="h-11 w-11 md:h-8 md:w-8 text-red-500 hover:text-red-700 hover:bg-red-50 dark:text-red-400 dark:hover:text-red-300 dark:hover:bg-red-950 disabled:text-muted-foreground disabled:hover:bg-transparent"
        >
          {isActionLoading && status.toLowerCase() === 'pending' ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <X className="h-5 w-5" />
          )}
        </Button>
      </div>

      {/* Approve Dialog */}
      <AlertDialog open={showApproveDialog} onOpenChange={setShowApproveDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{translate(t, 'requests.dialogs.approveTitle')}</AlertDialogTitle>
            <AlertDialogDescription>
              {translate(t, 'requests.dialogs.approveMessage')} {requestId}?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isLoading}>{translate(t, 'requests.dialogs.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={handleApprove} disabled={isLoading}>
              {isLoading ? translate(t, 'requests.dialogs.approving') : translate(t, 'requests.dialogs.approve')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Reject Dialog */}
      <AlertDialog open={showRejectDialog} onOpenChange={setShowRejectDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{translate(t, 'requests.dialogs.rejectTitle')}</AlertDialogTitle>
            <AlertDialogDescription>
              {translate(t, 'requests.dialogs.rejectMessage')} {requestId}?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isLoading}>{translate(t, 'requests.dialogs.cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleReject}
              disabled={isLoading}
              className="bg-red-500 hover:bg-red-600 dark:bg-red-600 dark:hover:bg-red-700"
            >
              {isLoading ? translate(t, 'requests.dialogs.rejecting') : translate(t, 'requests.dialogs.reject')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
