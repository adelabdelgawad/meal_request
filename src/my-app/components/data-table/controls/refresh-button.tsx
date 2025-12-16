"use client";

import React from "react";
import { Button } from "../ui/button";
import { RefreshCw } from "lucide-react";
import { useLanguage, translate } from "@/hooks/use-language";

interface RefreshButtonProps {
  onRefresh: () => void;
}

export const RefreshButton: React.FC<RefreshButtonProps> = ({
  onRefresh,
}) => {
  const { t } = useLanguage();

  return (
    <Button
      onClick={onRefresh}
      variant="default"
      size="default"
      icon={<RefreshCw className="w-4 h-4" />}
      tooltip={translate(t, 'table.refreshTooltip')}
    >
      {translate(t, 'table.refresh')}
    </Button>
  );
};
