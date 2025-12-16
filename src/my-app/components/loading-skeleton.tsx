import React from "react";

interface LoadingSkeletonProps {
  rows?: number;
  className?: string;
}

export default function LoadingSkeleton({ rows = 5, className = "" }: LoadingSkeletonProps) {
  return (
    <div className={`animate-pulse space-y-4 ${className}`}>
      {/* Header skeleton */}
      <div className="h-12 bg-gray-200 rounded-md w-full" />

      {/* Table rows skeleton */}
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="flex space-x-4">
          <div className="h-16 bg-gray-100 rounded-md flex-1" />
        </div>
      ))}
    </div>
  );
}
