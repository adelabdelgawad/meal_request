"use client";

import React, { ReactNode } from "react";
import { useLanguage } from "@/hooks/use-language";

interface DynamicTableBarProps {
  left?: ReactNode;
  middle?: ReactNode;
  right?: ReactNode;
  variant?: "header" | "controller";
  hasSelection?: boolean;
}

export const DynamicTableBar: React.FC<DynamicTableBarProps> = ({
  left,
  middle,
  right,
  variant = "header",
  hasSelection = false,
}) => {
  const { language } = useLanguage();
  const isRtl = language === "ar";

  const bgColor =
    variant === "controller"
      ? hasSelection
        ? "bg-accent border-accent"
        : "bg-muted/50 border-border"
      : "bg-card border-border";

  return (
    <div className={`border px-4 py-3 transition-colors ${bgColor}`}>
      <div className={`flex items-center justify-between gap-4 ${isRtl ? "flex-row-reverse" : ""}`}>
        {/* Left Section (in RTL becomes right visually) */}
        <div className={`flex items-center gap-2 flex-1 ${isRtl ? "flex-row-reverse" : ""}`}>
          {left}
        </div>

        {/* Middle Section */}
        {middle && (
          <div className={`flex items-center gap-2 flex-1 justify-center ${isRtl ? "flex-row-reverse" : ""}`}>
            {middle}
          </div>
        )}

        {/* Right Section (in RTL becomes left visually) */}
        <div className={`flex items-center gap-2 flex-1 justify-end ${isRtl ? "flex-row-reverse" : ""}`}>
          {right}
        </div>
      </div>
    </div>
  );
};