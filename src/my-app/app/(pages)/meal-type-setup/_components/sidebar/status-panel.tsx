"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle2, XCircle, List, UtensilsCrossed } from "lucide-react";
import { useLanguage, translate } from "@/hooks/use-language";
import { cn } from "@/lib/utils";

interface StatusPanelProps {
  activeCount: number;
  inactiveCount: number;
  totalCount: number;
}

export function StatusPanel({ activeCount, inactiveCount, totalCount }: StatusPanelProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { t } = useLanguage();

  const currentFilter = searchParams?.get("active_only") || "all";

  const handleFilterChange = (filter: string) => {
    const params = new URLSearchParams(searchParams?.toString());

    if (filter === "all") {
      params.delete("active_only");
    } else {
      params.set("active_only", filter);
    }

    params.set("page", "1"); // Reset to first page

    router.push(`?${params.toString()}`);
  };

  const filters = [
    {
      id: "all",
      label: translate(t, "mealTypes.status.all") || "All",
      count: totalCount,
      icon: List,
      color: "text-blue-600 dark:text-blue-400",
      bgColor: "bg-blue-50 dark:bg-blue-950/30",
    },
    {
      id: "true",
      label: translate(t, "mealTypes.status.active") || "Active",
      count: activeCount,
      icon: CheckCircle2,
      color: "text-green-600 dark:text-green-400",
      bgColor: "bg-green-50 dark:bg-green-950/30",
    },
    {
      id: "false",
      label: translate(t, "mealTypes.status.inactive") || "Inactive",
      count: inactiveCount,
      icon: XCircle,
      color: "text-orange-600 dark:text-orange-400",
      bgColor: "bg-orange-50 dark:bg-orange-950/30",
    },
  ];

  return (
    <div className="h-full flex flex-col p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2 pb-2 border-b">
        <UtensilsCrossed className="h-5 w-5 text-primary" />
        <h2 className="font-semibold">
          {translate(t, "mealTypes.title") || "Meal Types"}
        </h2>
      </div>

      {/* Filters */}
      <div className="space-y-2">
        <h3 className="text-sm font-medium text-muted-foreground mb-3">
          {translate(t, "mealTypes.filters.showAll") || "Filter by Status"}
        </h3>

        {filters.map((filter) => {
          const Icon = filter.icon;
          const isActive = currentFilter === filter.id;

          return (
            <Button
              key={filter.id}
              variant={isActive ? "secondary" : "ghost"}
              className={cn(
                "w-full justify-start gap-3 h-auto py-3",
                isActive && "bg-secondary"
              )}
              onClick={() => handleFilterChange(filter.id)}
            >
              <div className={cn("p-2 rounded-lg", filter.bgColor)}>
                <Icon className={cn("h-4 w-4", filter.color)} />
              </div>
              <div className="flex-1 text-left">
                <div className="font-medium text-sm">{filter.label}</div>
                <div className="text-xs text-muted-foreground">
                  {filter.count} {filter.count === 1 ? "item" : "items"}
                </div>
              </div>
              {isActive && (
                <Badge variant="secondary" className="ml-auto">
                  Active
                </Badge>
              )}
            </Button>
          );
        })}
      </div>

      {/* Stats Summary */}
      <Card className="mt-auto">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Total:</span>
            <span className="font-semibold">{totalCount}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Active:</span>
            <span className="font-semibold text-green-600">{activeCount}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Inactive:</span>
            <span className="font-semibold text-orange-600">{inactiveCount}</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
