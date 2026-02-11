import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { LucideIcon } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";

interface StatusCircleProps {
  count: number;
  color: string;
  label: string;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  showTooltip?: boolean;
  icon?: LucideIcon;
  percentage?: number; // Progress percentage (0-100)
  statusValue?: string;
  queryParam?: string; // Query parameter name (default: "status")
}

export function StatusCircle({
  count,
  color,
  label,
  size = "md",
  showLabel = true,
  showTooltip = false,
  icon: Icon,
  percentage = 75,
  statusValue,
  queryParam = "status",
}: StatusCircleProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [, startTransition] = useTransition();

  const sizeClasses: Record<"sm" | "md" | "lg", string> = {
    sm: "w-12 h-12",
    md: "w-24 h-24",
    lg: "w-40 h-40",
  };

  const innerSizeClasses: Record<"sm" | "md" | "lg", string> = {
    sm: "w-10 h-10",
    md: "w-20 h-20",
    lg: "w-36 h-36",
  };

  const textSizes: Record<"sm" | "md" | "lg", string> = {
    sm: "text-lg",
    md: "text-2xl",
    lg: "text-4xl",
  };

  const _iconSizes: Record<"sm" | "md" | "lg", string> = {
    sm: "h-4 w-4",
    md: "h-6 w-6",
    lg: "h-10 w-10",
  };

  const labelSizes: Record<"sm" | "md" | "lg", string> = {
    sm: "text-xs",
    md: "text-xs",
    lg: "text-xs",
  };

  const handleClick = () => {
    if (!statusValue) {
      return;
    }

    // Use startTransition to batch URL updates and prevent cascading re-renders
    startTransition(() => {
      const params = new URLSearchParams(searchParams?.toString());

      if (statusValue === "all") {
        // Remove the filter
        params.delete(queryParam);
      } else {
        // Set the filter value
        params.set(queryParam, statusValue);
      }

      // Reset role filter when status changes
      params.delete("role");

      // Reset to page 1 when filtering (keep limit unchanged)
      params.set("page", "1");

      router.push(`?${params.toString()}`);
    });
  };

  // Get current query param value
  const currentValue = searchParams?.get(queryParam);

  // Determine if this circle is currently active
  const _isActive = statusValue === "all"
    ? !currentValue // "all" is active when there's no filter
    : currentValue === statusValue; // specific value is active when it matches

  // Calculate the conic gradient based on percentage
  const gradientDegrees = (percentage / 100) * 360;
  const conicGradient =
    size === "lg"
      ? `conic-gradient(${color} 0deg, ${color} ${gradientDegrees}deg, #e5e7eb ${gradientDegrees}deg)`
      : undefined;

  const circle = (
    <div className="flex flex-col items-center gap-2">
      <div
        className={`${sizeClasses[size]} rounded-full flex items-center justify-center cursor-pointer transition-all ${
          size === "lg" ? "" : "shadow-md bg-white border-4 font-bold"
        } ${
          _isActive
            ? "opacity-100 scale-105"
            : "opacity-60 hover:opacity-80 hover:scale-102"
        }`}
        style={
          size === "lg"
            ? { background: conicGradient }
            : { borderColor: color, color: color }
        }
        onClick={handleClick}
      >
        {size === "lg" ? (
          <div
            className={`${innerSizeClasses[size]} bg-white rounded-full flex flex-col items-center justify-center`}
          >
            {Icon && <Icon className={`${_iconSizes[size]} text-gray-800`} />}
            <div className={`${textSizes[size]} font-bold text-gray-800 mt-2`}>
              {count}
            </div>
            {showLabel && (
              <div className={`${labelSizes[size]} text-gray-600 font-medium`}>
                {label}
              </div>
            )}
          </div>
        ) : (
          <span className={`${textSizes[size]} font-bold`} style={{ color }}>
            {count}
          </span>
        )}
      </div>
      {showLabel && size !== "lg" && (
        <span className="text-xs text-gray-600 font-medium text-center">
          {label}
        </span>
      )}
    </div>
  );

  if (showTooltip) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>{circle}</TooltipTrigger>
          <TooltipContent side="right">
            <p>{label}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return circle;
}

