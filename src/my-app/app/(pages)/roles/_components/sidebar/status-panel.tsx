"use client";

import React from "react";
import { Shield } from "lucide-react";
import { StatusPanel as BaseStatusPanel } from "@/components/data-table";

type StatusPanelProps = {
  allRoles: number;
  activeRolesCount: number;
  inactiveRolesCount: number;
};

export const StatusPanel: React.FC<StatusPanelProps> = ({
  allRoles,
  activeRolesCount,
  inactiveRolesCount,
}) => {
  return (
    <BaseStatusPanel
      totalCount={allRoles}
      activeCount={activeRolesCount}
      inactiveCount={inactiveRolesCount}
      entityLabel="Role"
      icon={Shield}
      queryParam="is_active"
    />
  );
};
