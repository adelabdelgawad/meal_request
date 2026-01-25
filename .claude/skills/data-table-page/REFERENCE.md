# Data Table Page Reference

Complete API and component reference for the data table page system.

## Shared Components

### DataTable

**Path:** `src/my-app/components/data-table/table/data-table.tsx`

TanStack React Table wrapper with mobile card support.

```typescript
interface DataTableProps<TData> {
  _data: TData[];                    // Data array to display
  columns: ColumnDef<TData>[];       // Column definitions
  onRowSelectionChange?: (rows: TData[]) => void;  // Selection callback
  renderToolbar?: (table: TanStackTable<TData>) => React.ReactNode;
  _isLoading?: boolean;              // Show loading overlay
  tableInstanceHook?: (table: TanStackTable<TData>) => void;
  enableRowSelection?: boolean;      // Default: true
  enableSorting?: boolean;           // Default: true
  getRowClassName?: (row: TData) => string;  // Custom row classes
  renderMobileCard?: (item: TData, index: number) => React.ReactNode;
}
```

**Usage:**
```tsx
<DataTable
  _data={items}
  columns={columns}
  onRowSelectionChange={setSelectedItems}
  _isLoading={isLoading}
  tableInstanceHook={setTableInstance}
/>
```

---

### Pagination

**Path:** `src/my-app/components/data-table/table/pagination.tsx`

URL-synced pagination using nuqs.

```typescript
interface PaginationProps {
  currentPage: number;
  totalPages: number;
  pageSize: number;
  totalItems: number;
}
```

**URL Parameters:**
- `page` - Current page number (1-indexed)
- `limit` - Items per page

**Usage:**
```tsx
<Pagination
  currentPage={page}
  totalPages={totalPages}
  pageSize={limit}
  totalItems={totalItems}
/>
```

---

### SearchInput

**Path:** `src/my-app/components/data-table/controls/search-input.tsx`

Debounced search input with URL sync.

```typescript
interface SearchInputProps {
  paramName?: string;        // URL param name (default: "filter")
  placeholder?: string;      // Placeholder text
  debounceMs?: number;       // Debounce delay (default: 500)
}
```

**Usage:**
```tsx
<SearchInput
  paramName="search"
  placeholder="Search products..."
  debounceMs={300}
/>
```

---

### ExportButton

**Path:** `src/my-app/components/data-table/actions/export-button.tsx`

CSV/Excel export with custom formatting.

```typescript
interface ExportButtonProps<TData> {
  table: TanStackTable<TData>;       // Table instance
  filename?: string;                  // Export filename
  page?: number;                      // Current page (for page export)
  valueFormatters?: Record<string, (value: unknown, row: TData) => string>;
  headerLabels?: Record<string, string>;  // Custom column headers
}
```

**Usage:**
```tsx
<ExportButton
  table={tableInstance}
  filename="products"
  valueFormatters={{
    price: (value) => `$${(value as number).toFixed(2)}`,
    roles: (_, row) => row.roleIds.map(id => roleMap.get(id)).join("; "),
  }}
  headerLabels={{
    isActive: "Status",
    createdAt: "Created Date",
  }}
/>
```

---

### TableHeader

**Path:** `src/my-app/components/data-table/table/table-header.tsx`

Standard header bar with search, export, print.

```typescript
interface TableHeaderProps<TData> {
  table: TanStackTable<TData>;
  filename?: string;
  showExport?: boolean;
  showPrint?: boolean;
  showSearch?: boolean;
  searchParamName?: string;
  leftContent?: React.ReactNode;
  rightContent?: React.ReactNode;
}
```

---

### TableController

**Path:** `src/my-app/components/data-table/table/table-controller.tsx`

Controller bar with bulk actions and column toggle.

```typescript
interface TableControllerProps<TData> {
  table: TanStackTable<TData>;
  selectedCount: number;
  onEnable?: () => void;
  onDisable?: () => void;
  showColumnToggle?: boolean;
  leftContent?: React.ReactNode;
  rightContent?: React.ReactNode;
}
```

---

### StatusPanel

**Path:** `src/my-app/components/data-table/sidebar/status-panel.tsx`

Left sidebar with summary statistics.

```typescript
interface StatusPanelProps {
  totalCount: number;
  activeCount: number;
  inactiveCount: number;
  filters?: FilterConfig[];
  children?: React.ReactNode;
}

interface FilterConfig {
  label: string;
  paramName: string;
  options: { value: string; label: string }[];
}
```

---

## SWR Configuration

### Recommended Options

```typescript
const swrOptions = {
  // Initial data from server component
  fallbackData: initialData,

  // Keep showing previous data while fetching new
  keepPreviousData: true,

  // Don't refetch on mount (server data is fresh)
  revalidateOnMount: false,

  // Refetch if cache is stale
  revalidateIfStale: true,

  // Reduce unnecessary refetches
  revalidateOnFocus: false,
  revalidateOnReconnect: false,
};
```

### Mutate Function

```typescript
// Update cache without refetch
await mutate(
  (currentData) => {
    // Return new data object
    return { ...currentData, items: newItems };
  },
  { revalidate: false }
);

// Force refetch from API
await mutate();
```

---

## API Layer

### Server API (serverApi)

**Path:** `src/my-app/lib/http/axios-server.ts`

Used in server actions for server-side data fetching.

```typescript
const result = await serverApi.get<ResponseType>("/endpoint", {
  params: { limit, skip, filter },
  useVersioning: true,  // Prepends /api/v1
});

if (result.ok) {
  return result.data;
}
```

### Client API (clientApi)

**Path:** `src/my-app/lib/http/axios-client.ts`

Used in client components for mutations.

```typescript
// GET
const result = await clientApi.get<ResponseType>("/endpoint");

// POST
const result = await clientApi.post<ResponseType>("/endpoint", data);

// PUT
const result = await clientApi.put<ResponseType>("/endpoint", data);

// PATCH
const result = await clientApi.patch<ResponseType>("/endpoint", data);

// DELETE
const result = await clientApi.delete("/endpoint");

// Check result
if (result.ok) {
  return result.data;
} else {
  throw new Error(result.error);
}
```

---

## Column Definition API

### ColumnDef Structure

```typescript
interface ColumnDef<TData> {
  // Identification
  id?: string;                        // Unique column ID
  accessorKey?: keyof TData;          // Data field accessor
  accessorFn?: (row: TData) => unknown;  // Custom accessor

  // Header
  header: string | ((context: HeaderContext) => ReactNode);

  // Cell
  cell: (context: CellContext) => ReactNode;

  // Sizing
  size?: number;                      // Default width
  minSize?: number;                   // Minimum width
  maxSize?: number;                   // Maximum width

  // Features
  enableSorting?: boolean;
  enableHiding?: boolean;
}
```

### Header Context

```typescript
interface HeaderContext<TData> {
  table: TanStackTable<TData>;
  column: Column<TData>;
  header: Header<TData>;
}
```

### Cell Context

```typescript
interface CellContext<TData> {
  table: TanStackTable<TData>;
  row: Row<TData>;
  column: Column<TData>;
  cell: Cell<TData>;
  getValue: () => unknown;
  renderValue: () => unknown;
}
```

---

## Type Definitions

### API Response Types

```typescript
// Paginated list response
interface ListResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
}

// With status counts
interface StatusListResponse<T> extends ListResponse<T> {
  activeCount: number;
  inactiveCount: number;
}

// Action result
interface ActionResult {
  success: boolean;
  message?: string;
  error?: string;
  data?: unknown;
}

// Bulk update response
interface BulkUpdateResponse<T> {
  updatedItems: T[];
  failedIds: string[];
}
```

### Common Entity Fields

```typescript
// Base entity
interface BaseEntity {
  id: string;
  createdAt: string;
  updatedAt: string | null;
}

// With status
interface StatusEntity extends BaseEntity {
  isActive: boolean;
}

// With bilingual names
interface BilingualEntity extends StatusEntity {
  nameEn: string;
  nameAr: string | null;
}
```

---

## Hooks

### useLanguage

**Path:** `src/my-app/hooks/use-language.ts`

```typescript
const { t, language, dir } = useLanguage();

// t - Translation object
// language - "en" | "ar"
// dir - "ltr" | "rtl"
```

### useSearchParams

**From:** `next/navigation`

```typescript
const searchParams = useSearchParams();
const page = searchParams?.get("page") || "1";
```

### useQueryState (nuqs)

**From:** `nuqs`

```typescript
import { useQueryState, parseAsInteger, parseAsString } from "nuqs";

const [page, setPage] = useQueryState("page", parseAsInteger.withDefault(1));
const [search, setSearch] = useQueryState("search", parseAsString.withDefault(""));
```

---

## Toast Notifications

**Path:** `src/my-app/components/ui/custom-toast.ts`

```typescript
import { toast } from "@/components/ui/custom-toast";

toast.success("Operation successful");
toast.error("Operation failed");
toast.info("Information message");
toast.warning("Warning message");
```

---

## Status Components

### StatusSwitch

**Path:** `src/my-app/components/ui/status-switch.tsx`

Toggle switch with confirmation dialog.

```typescript
interface StatusSwitchProps {
  checked: boolean;
  onToggle: () => Promise<void>;
  title?: string;           // Confirmation dialog title
  description?: string;     // Confirmation dialog description
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
}
```

### StatusBadge

**Path:** `src/my-app/components/data-table/ui/status-badge.tsx`

```typescript
interface StatusBadgeProps {
  isActive: boolean;
  activeLabel?: string;
  inactiveLabel?: string;
}
```

---

## Next.js API Routes

### Route Handler Pattern

```typescript
// app/api/{feature}/route.ts
import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";

export async function GET(request: NextRequest) {
  const session = await getServerSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const searchParams = request.nextUrl.searchParams;
  const limit = searchParams.get("limit") || "10";
  const skip = searchParams.get("skip") || "0";

  // Forward to backend
  const response = await fetch(`${BACKEND_URL}/api/v1/endpoint?limit=${limit}&skip=${skip}`, {
    headers: {
      Authorization: `Bearer ${session.accessToken}`,
    },
  });

  const data = await response.json();
  return NextResponse.json(data);
}
```

---

## Error Handling

### API Error Pattern

```typescript
try {
  const result = await apiCall();
  if (!result.ok) {
    throw new Error(result.error || "Operation failed");
  }
  return result.data;
} catch (error) {
  const apiError = error as {
    response?: { data?: { detail?: string } };
    message?: string;
  };
  const message = apiError.response?.data?.detail ||
                  apiError.message ||
                  "Unknown error";
  toast.error(message);
  throw error;
}
```

### Error Boundary

```typescript
import { ErrorBoundary } from "@/components/ErrorBoundary";

<ErrorBoundary fallback={<ErrorFallback />}>
  <TableComponent />
</ErrorBoundary>
```
