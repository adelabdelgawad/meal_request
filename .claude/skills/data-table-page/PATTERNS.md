# Data Table Page Implementation Patterns

Critical patterns that MUST be followed when building data table pages.

## 1. Server-Side Data Fetching Pattern (MANDATORY)

The page.tsx MUST be a Server Component that fetches initial data.

### Correct Pattern

```typescript
// app/(pages)/{feature}/page.tsx
import { getData } from "@/lib/actions/{feature}.actions";
import { getRoles } from "@/lib/actions/roles.actions";
import DataTable from "./_components/table/{feature}-table";

export default async function FeaturePage({
  searchParams,
}: {
  searchParams: Promise<{
    page?: string;
    limit?: string;
    search?: string;
    is_active?: string;
    // Add other filter params
  }>;
}) {
  // Await searchParams (Next.js 15+)
  const params = await searchParams;
  const { page, limit, search, is_active } = params;

  // Parse pagination
  const pageNumber = Number(page) || 1;
  const limitNumber = Number(limit) || 10;
  const skip = (pageNumber - 1) * limitNumber;

  // Build filters object (snake_case for URL params)
  const filters = {
    is_active,
    search,
  };

  // Fetch initial data server-side
  const data = await getData(limitNumber, skip, filters);

  // Fetch related data needed for forms
  const roles = await getRoles({ limit: 1000, skip: 0 });

  return (
    <DataTable
      initialData={data}
      roles={roles}
    />
  );
}
```

### DO NOT

```typescript
// ❌ WRONG - Client-side fetching in page
"use client";
export default function FeaturePage() {
  const [data, setData] = useState(null);
  useEffect(() => {
    fetchData().then(setData);  // ❌ No server-side rendering
  }, []);
}

// ❌ WRONG - Not awaiting searchParams
export default async function FeaturePage({ searchParams }) {
  const page = searchParams.page;  // ❌ Must await in Next.js 15+
}
```

---

## 2. SWR Setup Pattern (MANDATORY)

The main table component uses SWR with specific configuration.

### Correct Pattern

```typescript
// _components/table/{feature}-table.tsx
"use client";

import useSWR from "swr";
import { clientApi } from "@/lib/http/axios-client";

interface TableProps {
  initialData: DataResponse | null;
  roles: RoleResponse[];
}

// Fetcher function for SWR
const fetcher = async (url: string): Promise<DataResponse> => {
  const response = await clientApi.get<DataResponse>(url);
  if (!response.ok) {
    throw new Error(response.error || "Failed to fetch");
  }
  return response.data;
};

export default function FeatureTable({ initialData, roles }: TableProps) {
  const searchParams = useSearchParams();

  // Read URL parameters
  const page = Number(searchParams?.get("page") || "1");
  const limit = Number(searchParams?.get("limit") || "10");
  const filter = searchParams?.get("filter") || "";

  // Build API URL with filters
  const params = new URLSearchParams();
  params.append("skip", ((page - 1) * limit).toString());
  params.append("limit", limit.toString());
  if (filter) params.append("search", filter);

  const apiUrl = `/api/feature?${params.toString()}`;

  // SWR hook with optimized configuration
  const { data, mutate, isLoading, error } = useSWR<DataResponse>(
    apiUrl,
    fetcher,
    {
      // ✅ Use server data as initial cache
      fallbackData: initialData ?? undefined,

      // ✅ Smooth transitions when changing filters
      keepPreviousData: true,

      // ✅ Don't refetch on mount (we have server data)
      revalidateOnMount: false,

      // ✅ Refetch if data is stale
      revalidateIfStale: true,

      // ✅ Reduce API calls
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
    }
  );

  // ... rest of component
}
```

### SWR Options Explained

| Option | Value | Why |
|--------|-------|-----|
| `fallbackData` | `initialData` | Use server-fetched data immediately |
| `keepPreviousData` | `true` | Show old data while fetching new (smooth UX) |
| `revalidateOnMount` | `false` | Server data is fresh, no need to refetch |
| `revalidateIfStale` | `true` | Refetch if cache is old |
| `revalidateOnFocus` | `false` | Reduce unnecessary API calls |
| `revalidateOnReconnect` | `false` | Reduce unnecessary API calls |

---

## 3. Cache Update Pattern (CRITICAL)

After mutations, update the SWR cache without refetching.

### Correct Pattern

```typescript
/**
 * Update specific items in SWR cache with server response
 * Also recalculates aggregate counts
 */
const updateItems = async (updatedItems: ItemResponse[]) => {
  await mutate(
    (currentData: DataResponse | undefined) => {
      if (!currentData) return currentData;

      // Create lookup map for efficient updates
      const updatedMap = new Map(
        updatedItems.map((item) => [item.id, item])
      );

      // Update items in list
      const updatedItemsList = currentData.items.map((item) =>
        updatedMap.has(item.id) ? updatedMap.get(item.id)! : item
      );

      // Recalculate counts
      const newActiveCount = updatedItemsList.filter((i) => i.isActive).length;
      const newInactiveCount = updatedItemsList.filter((i) => !i.isActive).length;

      return {
        ...currentData,
        items: updatedItemsList,
        activeCount: newActiveCount,
        inactiveCount: newInactiveCount,
      };
    },
    { revalidate: false }  // ✅ Don't refetch from API
  );
};
```

### Key Points

1. **Return new object**: Don't mutate currentData directly
2. **Use Map for lookups**: Efficient O(1) lookups
3. **Recalculate counts**: Keep sidebar stats in sync
4. **revalidate: false**: Prevent unnecessary API call

### For Adding New Items

```typescript
const addItem = async (newItem: ItemResponse) => {
  await mutate(
    (currentData) => {
      if (!currentData) return currentData;
      return {
        ...currentData,
        items: [newItem, ...currentData.items],  // Add at start
        total: currentData.total + 1,
        activeCount: newItem.isActive
          ? currentData.activeCount + 1
          : currentData.activeCount,
      };
    },
    { revalidate: false }
  );
};
```

### For Deleting Items

```typescript
const removeItem = async (itemId: string) => {
  await mutate(
    (currentData) => {
      if (!currentData) return currentData;
      const removedItem = currentData.items.find((i) => i.id === itemId);
      return {
        ...currentData,
        items: currentData.items.filter((i) => i.id !== itemId),
        total: currentData.total - 1,
        activeCount: removedItem?.isActive
          ? currentData.activeCount - 1
          : currentData.activeCount,
      };
    },
    { revalidate: false }
  );
};
```

---

## 4. Mutation Flow Pattern (CRITICAL)

Every mutation MUST follow this exact sequence.

### Correct Pattern

```typescript
// In column definition or action handler
const handleToggleStatus = async (item: ItemResponse) => {
  if (!item.id) return;

  const newStatus = !item.isActive;

  // 1. Mark as updating (show loading spinner)
  markUpdating([item.id]);

  try {
    // 2. Call API and wait for server response
    const result = await toggleItemStatus(item.id, newStatus);

    // 3. Update cache with server response (NOT local state)
    await updateItems([result]);

    // 4. Show success toast
    toast.success(newStatus ? "Enabled successfully" : "Disabled successfully");

  } catch (error) {
    // 5. Handle error
    console.error("Failed to toggle status:", error);
    toast.error("Failed to update status");

  } finally {
    // 6. Clear loading state (always runs)
    clearUpdating([item.id]);
  }
};
```

### Flow Diagram

```
User Action
    ↓
markUpdating([id])           → UI shows loading spinner on row
    ↓
API Call (await)             → Send request to backend
    ↓
Server Response              → Backend returns updated item
    ↓
updateItems([result])        → Update SWR cache with response
    ↓
toast.success()              → Notify user
    ↓
clearUpdating([id])          → Remove loading spinner
```

### DO NOT

```typescript
// ❌ WRONG - Optimistic update before API response
markUpdating([item.id]);
updateItems([{ ...item, isActive: newStatus }]);  // ❌ Don't update before API
const result = await toggleItemStatus(item.id, newStatus);

// ❌ WRONG - Not waiting for API response
toggleItemStatus(item.id, newStatus);  // ❌ Missing await
updateItems([item]);  // ❌ Using stale data

// ❌ WRONG - Not clearing loading state on error
try {
  const result = await toggleItemStatus(item.id, newStatus);
  clearUpdating([item.id]);  // ❌ Only clears on success
} catch (error) {
  // Loading state stuck!
}

// ❌ WRONG - Using mutate() without function
await mutate();  // ❌ This refetches from API, use updateItems instead
```

---

## 5. Loading State Tracking Pattern

Track which rows are being updated for UI feedback.

### Correct Pattern

```typescript
// In table component
const [updatingIds, setUpdatingIds] = useState<Set<string>>(new Set());

const markUpdating = (ids: string[]) => {
  setUpdatingIds((prev) => {
    const next = new Set(prev);
    ids.forEach((id) => next.add(id));
    return next;
  });
};

const clearUpdating = (ids?: string[]) => {
  setUpdatingIds((prev) => {
    if (!ids) return new Set();  // Clear all
    const next = new Set(prev);
    ids.forEach((id) => next.delete(id));
    return next;
  });
};

// Pass to column definitions
const columns = createColumns({
  updatingIds,
  markUpdating,
  clearUpdating,
  updateItems,
  // ...
});
```

### In Column Cell

```typescript
cell: ({ row }) => {
  const item = row.original;
  const isRowUpdating = Boolean(item.id && updatingIds.has(item.id));

  return (
    <div className={isRowUpdating ? "opacity-60 pointer-events-none" : ""}>
      {isRowUpdating && <Loader2 className="animate-spin" />}
      {!isRowUpdating && (
        <StatusSwitch
          checked={item.isActive}
          onToggle={() => handleToggle(item)}
        />
      )}
    </div>
  );
};
```

---

## 6. Context API Pattern for Actions

Share CRUD actions with nested components via Context.

### Correct Pattern

```typescript
// context/{feature}-actions-context.tsx
"use client";

import { createContext, useContext, ReactNode } from "react";

interface ActionsContextType {
  onToggleStatus: (id: string, isActive: boolean) => Promise<ActionResult>;
  onUpdate: (id: string, data: UpdateData) => Promise<ActionResult>;
  updateItems: (items: ItemResponse[]) => Promise<void>;
  onBulkUpdate: (ids: string[], isActive: boolean) => Promise<ActionResult>;
  onRefresh: () => Promise<ActionResult>;
}

interface DataContextType {
  roles: RoleResponse[];
  departments: DepartmentResponse[];
}

type ContextType = ActionsContextType & DataContextType;

const Context = createContext<ContextType | null>(null);

interface ProviderProps {
  children: ReactNode;
  actions: ActionsContextType;
  roles: RoleResponse[];
  departments: DepartmentResponse[];
}

export function FeatureProvider({
  children,
  actions,
  roles,
  departments,
}: ProviderProps) {
  const value: ContextType = {
    ...actions,
    roles,
    departments,
  };

  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useFeatureContext() {
  const context = useContext(Context);
  if (!context) {
    throw new Error("useFeatureContext must be used within FeatureProvider");
  }
  return context;
}

// Convenience hooks
export function useFeatureActions() {
  const { onToggleStatus, onUpdate, updateItems, onBulkUpdate, onRefresh } =
    useFeatureContext();
  return { onToggleStatus, onUpdate, updateItems, onBulkUpdate, onRefresh };
}

export function useRoles() {
  const { roles } = useFeatureContext();
  return roles;
}
```

### Usage in Table Component

```typescript
// Define actions object
const actions = {
  onToggleStatus: async (id, isActive) => { /* ... */ },
  onUpdate: async (id, data) => { /* ... */ },
  updateItems,
  onBulkUpdate: async (ids, isActive) => { /* ... */ },
  onRefresh: async () => { await mutate(); return { success: true }; },
};

// Wrap children
return (
  <FeatureProvider actions={actions} roles={roles} departments={departments}>
    <TableBody />
  </FeatureProvider>
);
```

### Usage in Nested Component

```typescript
// In modal/edit-sheet.tsx
function EditSheet({ item, onClose }) {
  const { updateItems, roles } = useFeatureContext();

  const handleSave = async (data) => {
    const result = await updateItem(item.id, data);
    await updateItems([result]);
    toast.success("Updated successfully");
    onClose();
  };
}
```

---

## 7. Column Definitions Pattern

Create columns with callbacks for mutations.

### Correct Pattern

```typescript
// _components/table/{feature}-table-columns.tsx
"use client";

import { ColumnDef } from "@tanstack/react-table";

interface ColumnsProps {
  updatingIds: Set<string>;
  mutate: () => void;
  updateItems: (items: ItemResponse[]) => Promise<void>;
  markUpdating: (ids: string[]) => void;
  clearUpdating: (ids?: string[]) => void;
  translations: ColumnTranslations;
  language: string;
}

export function createColumns({
  updatingIds,
  updateItems,
  markUpdating,
  clearUpdating,
  translations: t,
  language,
}: ColumnsProps): ColumnDef<ItemResponse>[] {
  return [
    // Select column
    {
      id: "select",
      header: ({ table }) => (
        <input
          type="checkbox"
          checked={table.getIsAllPageRowsSelected()}
          onChange={(e) => table.toggleAllPageRowsSelected(e.target.checked)}
          disabled={updatingIds.size > 0}
        />
      ),
      cell: ({ row }) => {
        const isUpdating = updatingIds.has(row.original.id);
        return (
          <div className={isUpdating ? "opacity-60" : ""}>
            {isUpdating ? (
              <Loader2 className="animate-spin" />
            ) : (
              <input
                type="checkbox"
                checked={row.getIsSelected()}
                onChange={(e) => row.toggleSelected(e.target.checked)}
              />
            )}
          </div>
        );
      },
      enableSorting: false,
      enableHiding: false,
      size: 50,
    },

    // Data columns
    {
      accessorKey: "name",
      header: () => <div className="text-center">{t.name}</div>,
      cell: (info) => (
        <div className="text-center">{info.getValue() as string}</div>
      ),
      size: 150,
    },

    // Status column with inline mutation
    {
      id: "isActive",
      accessorKey: "isActive",
      header: () => <div className="text-center">{t.active}</div>,
      cell: ({ row }) => {
        const item = row.original;
        const isUpdating = updatingIds.has(item.id);

        return (
          <div className={isUpdating ? "opacity-60 pointer-events-none" : ""}>
            <StatusSwitch
              checked={item.isActive}
              onToggle={async () => {
                markUpdating([item.id]);
                try {
                  const result = await toggleStatus(item.id, !item.isActive);
                  await updateItems([result]);
                  toast.success(t.updateSuccess);
                } finally {
                  clearUpdating([item.id]);
                }
              }}
            />
          </div>
        );
      },
      size: 80,
    },

    // Actions column (populated in table body)
    {
      id: "actions",
      header: () => <div className="text-center">{t.actions}</div>,
      cell: () => <div />,  // Populated via render prop
      enableSorting: false,
      enableHiding: false,
      size: 180,
    },
  ];
}
```

---

## 8. Bulk Operations Pattern

Handle multiple item updates efficiently.

### Correct Pattern

```typescript
const handleBulkDisable = async (selectedIds: string[]) => {
  // 1. Filter to items that need action
  const itemsToDisable = items.filter(
    (item) => selectedIds.includes(item.id) && item.isActive
  );

  if (itemsToDisable.length === 0) {
    toast.info("All selected items are already disabled");
    return;
  }

  const idsToDisable = itemsToDisable.map((i) => i.id);

  // 2. Mark all as updating
  markUpdating(idsToDisable);

  try {
    // 3. Single bulk API call
    const response = await bulkUpdateStatus(idsToDisable, false);

    // 4. Update cache with all results
    if (response.updatedItems?.length > 0) {
      await updateItems(response.updatedItems);
    }

    // 5. Clear selection
    table.resetRowSelection();

    // 6. Show success
    toast.success(`Disabled ${response.updatedItems.length} items`);

  } catch (error) {
    toast.error("Failed to disable items");
  } finally {
    // 7. Clear all loading states
    clearUpdating();
  }
};
```

---

## 9. Server Action Pattern

Server actions for data fetching (runs on server).

### Correct Pattern

```typescript
// lib/actions/{feature}.actions.ts
"use server";

import { serverApi } from "@/lib/http/axios-server";
import type { DataResponse, ItemResponse } from "@/types/{feature}";

export async function getData(
  limit: number = 10,
  skip: number = 0,
  filters?: {
    is_active?: string;
    search?: string;
  }
): Promise<DataResponse | null> {
  try {
    // Build params (snake_case for URL)
    const params: Record<string, string | number> = { limit, skip };
    if (filters?.is_active) params.is_active = filters.is_active;
    if (filters?.search) params.search = filters.search;

    const result = await serverApi.get<DataResponse>("/api/endpoint", {
      params,
      useVersioning: true,  // Routes to /api/v1/...
    });

    if (result.ok && result.data) {
      return result.data;
    }

    if (!result.ok) {
      console.error("Failed to fetch:", result.error);
    }
    return null;
  } catch (error) {
    console.error("Error in getData:", error);
    return null;
  }
}
```

---

## 10. Client API Pattern

Client-side API calls for mutations.

### Correct Pattern

```typescript
// lib/api/{feature}.ts
import { clientApi } from "@/lib/http/axios-client";
import type { ItemResponse, CreateData, UpdateData } from "@/types/{feature}";

/**
 * Toggle item active status
 */
export async function toggleStatus(
  id: string,
  isActive: boolean
): Promise<ItemResponse> {
  const result = await clientApi.put<ItemResponse>(
    `/api/endpoint/${id}/status`,
    { isActive }  // camelCase in request body
  );

  if (!result.ok) {
    throw new Error(result.error || "Failed to toggle status");
  }

  return result.data;
}

/**
 * Create new item
 */
export async function createItem(data: CreateData): Promise<ItemResponse> {
  const result = await clientApi.post<ItemResponse>("/api/endpoint", data);

  if (!result.ok) {
    throw new Error(result.error || "Failed to create item");
  }

  return result.data;
}

/**
 * Update item
 */
export async function updateItem(
  id: string,
  data: UpdateData
): Promise<ItemResponse> {
  const result = await clientApi.put<ItemResponse>(`/api/endpoint/${id}`, data);

  if (!result.ok) {
    throw new Error(result.error || "Failed to update item");
  }

  return result.data;
}

/**
 * Delete item
 */
export async function deleteItem(id: string): Promise<void> {
  const result = await clientApi.delete(`/api/endpoint/${id}`);

  if (!result.ok) {
    throw new Error(result.error || "Failed to delete item");
  }
}

/**
 * Bulk update status
 */
export async function bulkUpdateStatus(
  ids: string[],
  isActive: boolean
): Promise<{ updatedItems: ItemResponse[] }> {
  const result = await clientApi.put<{ updatedItems: ItemResponse[] }>(
    "/api/endpoint/status",
    { ids, isActive }  // camelCase
  );

  if (!result.ok) {
    throw new Error(result.error || "Failed to bulk update");
  }

  return result.data;
}
```

---

## Anti-Patterns Summary

| Anti-Pattern | Why It's Wrong | Correct Approach |
|--------------|----------------|------------------|
| useState for server data | No caching, no deduping | Use SWR with fallbackData |
| mutate() without function | Causes refetch | Use mutate(fn, { revalidate: false }) |
| Optimistic update before API | Shows wrong data on failure | Update after API success |
| Not clearing loading state | Stuck spinners | Always use finally block |
| Direct cache mutation | Breaks React updates | Return new object from mutate fn |
| Skip context for actions | Prop drilling mess | Use FeatureProvider pattern |
| Fetch in useEffect | No SSR, loading flash | Server component + SWR |
