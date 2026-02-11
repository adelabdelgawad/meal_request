"use client";

import React, { useState } from "react";
import { Button } from "@/components/data-table/ui/button";
import { AddRoleSheet } from "../modal/add-role-sheet";
import { Plus } from "lucide-react";
import { useLanguage } from "@/hooks/use-language";
import { useRolesActions } from "@/app/(pages)/setting/roles/context/roles-actions-context";

export const AddRoleButton: React.FC = () => {
  const { t } = useLanguage();
  const settingRoles = (t as Record<string, unknown>).settingRoles as Record<string, string> | undefined;
  const addRoleText = settingRoles?.addRole || "Add Role";
  const addRoleTooltip = settingRoles?.addRoleTooltip || "Add new role";

  const [isOpen, setIsOpen] = useState(false);
  const { mutate } = useRolesActions();

  return (
    <>
      <Button
        onClick={() => setIsOpen(true)}
        variant="primary"
        size="default"
        icon={<Plus className="w-4 h-4" />}
        tooltip={addRoleTooltip}
      >
        {addRoleText}
      </Button>

      <AddRoleSheet
        open={isOpen}
        onOpenChange={setIsOpen}
        onMutate={mutate}
      />
    </>
  );
};
