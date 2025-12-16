"use client";

import React from "react";
import { Button } from "@/components/data-table";
import { toast } from "@/components/ui/custom-toast";
import { AddUserSheet } from "../modal/add-user-sheet";
import { createUser } from "@/lib/api/users";
import { UserPlus } from "lucide-react";
import type { UserCreate } from "@/types/users";
import { useLanguage, translate } from "@/hooks/use-language";

interface AddUserButtonProps {
  onAdd: () => void;
}

export const AddUserButton: React.FC<AddUserButtonProps> = ({ onAdd }) => {
  const { t } = useLanguage();
  const [isOpen, setIsOpen] = React.useState(false);

  const handleSave = async (user: UserCreate): Promise<void> => {
    try {
      await createUser(user);
      onAdd();
      setIsOpen(false);
      toast.success(translate(t, 'users.addUserSuccess'));
    } catch (err: unknown) {
      if (err instanceof Error) {
        toast.error(err.message || translate(t, 'users.addUserFailed'));
      } else {
        toast.error(translate(t, 'users.addUserFailed'));
      }
    }
  };

  return (
    <>
      <Button
        onClick={() => setIsOpen(true)}
        variant="primary"
        size="default"
        icon={<UserPlus className="w-4 h-4" />}
        tooltip={translate(t, 'users.addUserTooltip')}
      >
        {translate(t, 'users.addUser')}
      </Button>

      <AddUserSheet
        open={isOpen}
        onOpenChange={setIsOpen}
        onSave={handleSave}
      />
    </>
  );
};
