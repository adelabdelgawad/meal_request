"use client";

import { User } from "lucide-react";
import { StatusPanel as BaseStatusPanel } from "@/components/data-table";
import { RoleStatusFilter } from "../filters/role-status-filter";
import { UserSourceFilter } from "../filters/user-source-filter";
import React from "react";
import type { SimpleRole } from "@/types/users";

type StatusPanelProps = {
  allUsers: number;
  activeUsersCount: number;
  inactiveUsersCount: number;
  roleOptions?: SimpleRole[];
};

export const StatusPanel: React.FC<StatusPanelProps> = ({
  allUsers,
  activeUsersCount,
  inactiveUsersCount,
  roleOptions = [],
}) => {
  return (
    <BaseStatusPanel
      totalCount={allUsers}
      activeCount={activeUsersCount}
      inactiveCount={inactiveUsersCount}
      entityLabel="User"
      icon={User}
      queryParam="is_active"
      extraContent={
        <>
          {roleOptions.length > 0 && (
            <RoleStatusFilter roleOptions={roleOptions} />
          )}
          <div className="border-t border-gray-200 dark:border-gray-700 my-2" />
          <UserSourceFilter />
        </>
      }
    />
  );
};
