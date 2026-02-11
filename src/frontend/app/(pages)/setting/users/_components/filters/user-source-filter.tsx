"use client";

import React, { useEffect, useState } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { Database, UserPen, Shield, ShieldOff } from "lucide-react";
import { useLanguage, translate } from "@/hooks/use-language";
import { getUserSources } from "@/lib/api/users";
import type { UserSourceMetadata } from "@/types/users";

/**
 * User Source and Override Filters
 * Allows filtering users by source type (HRIS/Manual) and override status
 */
export const UserSourceFilter: React.FC = () => {
  const { t, language } = useLanguage();
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const currentSource = searchParams?.get("user_source");
  const currentOverride = searchParams?.get("status_override");

  const [sources, setSources] = useState<UserSourceMetadata[]>([]);

  // Fetch user source metadata on mount
  useEffect(() => {
    const fetchSources = async () => {
      try {
        const data = await getUserSources();
        setSources(data);
      } catch (error) {
        console.error("Failed to fetch user sources:", error);
        // Use fallback sources
        setSources([
          {
            code: "hris",
            nameEn: "HRIS User",
            nameAr: "مستخدم HRIS",
            descriptionEn: "User from HRIS system",
            descriptionAr: "مستخدم من نظام الموارد البشرية",
            icon: "database",
            color: "blue",
            canOverride: true,
          },
          {
            code: "manual",
            nameEn: "Manual User",
            nameAr: "مستخدم يدوي",
            descriptionEn: "Manually created user",
            descriptionAr: "مستخدم تم إنشاؤه يدويًا",
            icon: "user-edit",
            color: "green",
            canOverride: false,
          },
        ]);
      }
    };
    fetchSources();
  }, []);

  const handleSourceClick = (sourceCode: string) => {
    const params = new URLSearchParams(searchParams?.toString());

    if (currentSource === sourceCode) {
      // Toggle off if already selected
      params.delete("user_source");
    } else {
      // Select new source
      params.set("user_source", sourceCode);
    }

    params.set("page", "1"); // Reset to first page
    router.push(`${pathname}?${params.toString()}`);
  };

  const handleOverrideClick = (value: string) => {
    const params = new URLSearchParams(searchParams?.toString());

    if (currentOverride === value) {
      // Toggle off if already selected
      params.delete("status_override");
    } else {
      // Select override status
      params.set("status_override", value);
    }

    params.set("page", "1"); // Reset to first page
    router.push(`${pathname}?${params.toString()}`);
  };

  const getSourceIcon = (iconName: string) => {
    return iconName === "database" ? Database : UserPen;
  };

  const getColorClasses = (color: string, isSelected: boolean) => {
    const baseClasses = "px-3 py-2 rounded-lg border-2 transition-all cursor-pointer flex items-center gap-2 text-sm font-medium";

    if (isSelected) {
      return `${baseClasses} ${
        color === "blue"
          ? "bg-blue-100 border-blue-500 text-blue-700 dark:bg-blue-900 dark:border-blue-400 dark:text-blue-300"
          : color === "green"
          ? "bg-green-100 border-green-500 text-green-700 dark:bg-green-900 dark:border-green-400 dark:text-green-300"
          : "bg-gray-100 border-gray-500 text-gray-700 dark:bg-gray-900 dark:border-gray-400 dark:text-gray-300"
      }`;
    }

    return `${baseClasses} border-gray-200 text-gray-600 hover:border-gray-300 dark:border-gray-700 dark:text-gray-400 dark:hover:border-gray-600`;
  };

  if (sources.length === 0) {
    return null;
  }

  return (
    <div className="px-4 py-4 space-y-4">
      {/* Source Filter */}
      <div>
        <div className="text-xs font-semibold text-muted-foreground mb-3">
          {language === "ar" ? "المصدر" : "Source"}
        </div>
        <div className="flex flex-wrap gap-2">
          {sources.map((source) => {
            const isSelected = currentSource === source.code;
            const Icon = getSourceIcon(source.icon);
            const label = language === "ar" ? source.nameAr : source.nameEn;

            return (
              <div
                key={source.code}
                onClick={() => handleSourceClick(source.code)}
                className={getColorClasses(source.color, isSelected)}
                title={language === "ar" ? source.descriptionAr : source.descriptionEn}
              >
                <Icon className="w-4 h-4" />
                <span>{label}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Override Filter */}
      <div>
        <div className="text-xs font-semibold text-muted-foreground mb-3">
          {language === "ar" ? "حالة التجاوز" : "Override Status"}
        </div>
        <div className="flex flex-wrap gap-2">
          {/* With Override */}
          <div
            onClick={() => handleOverrideClick("true")}
            className={
              currentOverride === "true"
                ? "px-3 py-2 rounded-lg border-2 transition-all cursor-pointer flex items-center gap-2 text-sm font-medium bg-amber-100 border-amber-500 text-amber-700 dark:bg-amber-900 dark:border-amber-400 dark:text-amber-300"
                : "px-3 py-2 rounded-lg border-2 transition-all cursor-pointer flex items-center gap-2 text-sm font-medium border-gray-200 text-gray-600 hover:border-gray-300 dark:border-gray-700 dark:text-gray-400 dark:hover:border-gray-600"
            }
            title={
              language === "ar"
                ? "إظهار المستخدمين الذين لديهم تجاوز نشط"
                : "Show users with active override"
            }
          >
            <Shield className="w-4 h-4" />
            <span>
              {language === "ar" ? "مع تجاوز" : "With Override"}
            </span>
          </div>

          {/* Without Override */}
          <div
            onClick={() => handleOverrideClick("false")}
            className={getColorClasses(
              "gray",
              currentOverride === "false"
            )}
            title={
              language === "ar"
                ? "إظهار المستخدمين بدون تجاوز نشط"
                : "Show users without active override"
            }
          >
            <ShieldOff className="w-4 h-4" />
            <span>
              {language === "ar" ? "بدون تجاوز" : "Without Override"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
