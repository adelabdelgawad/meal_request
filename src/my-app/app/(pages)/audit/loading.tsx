export default function AuditLoading() {
  return (
    <div className="flex flex-col h-full p-4 md:p-6">
      <div className="h-8 w-48 bg-muted animate-pulse rounded mb-4" />
      <div className="flex gap-4 mb-4">
        <div className="h-10 w-24 bg-muted animate-pulse rounded" />
        <div className="h-10 w-32 bg-muted animate-pulse rounded" />
        <div className="flex-1" />
        <div className="h-10 w-48 bg-muted animate-pulse rounded" />
      </div>
      <div className="flex-1 bg-muted animate-pulse rounded" />
    </div>
  );
}
