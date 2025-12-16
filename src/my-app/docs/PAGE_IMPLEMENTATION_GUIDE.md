# Page Implementation Guide

This guide provides a step-by-step approach to creating a data management page (like the Users page) with full internationalization, RTL support, and modern React patterns.

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [File Structure](#file-structure)
3. [Implementation Steps](#implementation-steps)
4. [Language Implementation](#language-implementation)
5. [Component Patterns](#component-patterns)
6. [Styling Guidelines](#styling-guidelines)
7. [Common Pitfalls](#common-pitfalls)

---

## Architecture Overview

### Tech Stack
- **Framework**: Next.js 14+ with App Router
- **Data Fetching**: Server Components + SWR for client-side updates
- **State Management**: URL state (nuqs) + React state
- **Table**: TanStack Table v8
- **i18n**: Custom useLanguage hook with JSON locale files
- **Styling**: Tailwind CSS with RTL support

### Data Flow
```
┌─────────────────────────────────────────────────────────────┐
│ 1. Server Component (page.tsx)                              │
│    - Fetch initial data from API                            │
│    - Await searchParams for filters                         │
│    - Pass data to Client Component                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Main Table Component (entity-table.tsx)                  │
│    - Client Component with "use client"                     │
│    - Use SWR for data fetching & caching                    │
│    - URL state management with nuqs                         │
│    - Provide context for child components                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Child Components                                         │
│    - Table Header (search, filters)                         │
│    - Status Panel (sidebar with counts)                     │
│    - Data Table (display rows)                              │
│    - Modals (add, edit, view)                               │
│    - Action Buttons                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

### Recommended Structure for a New Page (e.g., "Roles")

```
app/(pages)/roles/
├── page.tsx                              # Server Component - Initial data fetch
├── context/
│   └── roles-actions-context.tsx        # Context provider for shared data
├── _components/
│   ├── table/
│   │   ├── roles-table.tsx              # Main table component (client)
│   │   ├── roles-table-header.tsx       # Search & controls
│   │   ├── roles-table-columns.tsx      # Column definitions
│   │   ├── roles-table-body.tsx         # Table body wrapper
│   │   ├── roles-table-actions.tsx      # Bulk actions
│   │   └── roles-table-controller.tsx   # SWR data fetching
│   ├── modal/
│   │   ├── add-role-sheet.tsx           # Add new role modal
│   │   ├── edit-role-sheet.tsx          # Edit role modal
│   │   └── view-role-sheet.tsx          # View role details
│   ├── sidebar/
│   │   └── status-panel.tsx             # Status sidebar
│   ├── filters/
│   │   └── [custom-filters].tsx         # Custom filter components
│   └── actions/
│       └── add-role-button.tsx          # Add button component
```

---

## Implementation Steps

### Step 1: Define Types

Create TypeScript interfaces in `/types/[entity].ts`:

```typescript
// types/roles.ts
export interface Role {
  id: string;
  name: string;
  nameEn?: string;
  nameAr?: string;
  descriptionEn?: string;
  descriptionAr?: string;
  isActive: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface RoleCreate {
  name: string;
  nameEn?: string;
  nameAr?: string;
  descriptionEn?: string;
  descriptionAr?: string;
}

export interface RoleUpdate extends Partial<RoleCreate> {
  isActive?: boolean;
}

export interface RolesListResponse {
  roles: Role[];
  total: number;
  activeCount: number;
  inactiveCount: number;
}
```

### Step 2: Create API Actions

Create server actions in `/lib/actions/[entity].actions.ts`:

```typescript
// lib/actions/roles.actions.ts
"use server";

import { apiClient } from "@/lib/http/axios-server";
import type { RolesListResponse } from "@/types/roles";

export async function getRoles(filters?: {
  limit?: number;
  skip?: number;
  is_active?: string;
  search?: string;
}): Promise<RolesListResponse> {
  const params = new URLSearchParams();

  if (filters?.limit) params.append("limit", filters.limit.toString());
  if (filters?.skip) params.append("skip", filters.skip.toString());
  if (filters?.is_active) params.append("is_active", filters.is_active);
  if (filters?.search) params.append("search", filters.search);

  const response = await apiClient.get(`/auth/roles?${params.toString()}`);
  return response.data;
}
```

### Step 3: Create Server Page Component

```typescript
// app/(pages)/roles/page.tsx
import { getRoles } from "@/lib/actions/roles.actions";
import RolesTable from "./_components/table/roles-table";

export default async function RolesPage({
  searchParams,
}: {
  searchParams: Promise<{
    is_active?: string;
    search?: string;
    page?: string;
    limit?: string;
  }>;
}) {
  const params = await searchParams;
  const { is_active, search, page, limit } = params;

  const pageNumber = Number(page) || 1;
  const limitNumber = Number(limit) || 10;
  const skip = (pageNumber - 1) * limitNumber;

  const filters = {
    is_active,
    search,
  };

  const roles = await getRoles({ ...filters, limit: limitNumber, skip });

  return <RolesTable initialData={roles} />;
}
```

### Step 4: Create Context Provider

```typescript
// app/(pages)/roles/context/roles-actions-context.tsx
"use client";

import React, { createContext, useContext, ReactNode } from "react";
import type { Role } from "@/types/roles";

interface RolesActionsContextType {
  roles: Role[];
}

const RolesActionsContext = createContext<RolesActionsContextType | undefined>(
  undefined
);

export function RolesActionsProvider({
  children,
  roles,
}: {
  children: ReactNode;
  roles: Role[];
}) {
  return (
    <RolesActionsContext.Provider value={{ roles }}>
      {children}
    </RolesActionsContext.Provider>
  );
}

export function useRoles() {
  const context = useContext(RolesActionsContext);
  if (!context) {
    throw new Error("useRoles must be used within RolesActionsProvider");
  }
  return context.roles;
}
```

### Step 5: Create Main Table Component

```typescript
// app/(pages)/roles/_components/table/roles-table.tsx
"use client";

import React from "react";
import { RolesActionsProvider } from "../../context/roles-actions-context";
import { RolesTableController } from "./roles-table-controller";
import type { RolesListResponse } from "@/types/roles";

interface RolesTableProps {
  initialData: RolesListResponse;
}

export default function RolesTable({ initialData }: RolesTableProps) {
  return (
    <RolesActionsProvider roles={initialData.roles}>
      <RolesTableController initialData={initialData} />
    </RolesActionsProvider>
  );
}
```

### Step 6: Create Table Controller with SWR

```typescript
// app/(pages)/roles/_components/table/roles-table-controller.tsx
"use client";

import React, { useState } from "react";
import useSWR from "swr";
import { useSearchParams } from "next/navigation";
import { DataTable } from "@/components/data-table";
import { RolesTableHeader } from "./roles-table-header";
import { StatusPanel } from "../sidebar/status-panel";
import { createRolesTableColumns } from "./roles-table-columns";
import type { RolesListResponse } from "@/types/roles";

const fetcher = async (url: string) => {
  const response = await fetch(url);
  if (!response.ok) throw new Error("Failed to fetch");
  return response.json();
};

interface RolesTableControllerProps {
  initialData: RolesListResponse;
}

export function RolesTableController({ initialData }: RolesTableControllerProps) {
  const searchParams = useSearchParams();
  const [updatingIds, setUpdatingIds] = useState<Set<string>>(new Set());

  // Build API URL from search params
  const params = new URLSearchParams(searchParams?.toString() || "");
  const apiUrl = `/api/roles?${params.toString()}`;

  // SWR for data fetching
  const { data, mutate, isLoading } = useSWR<RolesListResponse>(
    apiUrl,
    fetcher,
    {
      fallbackData: initialData,
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
    }
  );

  const roles = data?.roles || [];
  const total = data?.total || 0;
  const activeCount = data?.activeCount || 0;
  const inactiveCount = data?.inactiveCount || 0;

  const page = Number(searchParams?.get("page")) || 1;
  const limit = Number(searchParams?.get("limit")) || 10;

  const columns = createRolesTableColumns({
    updatingIds,
    mutate,
    markUpdating: (ids: string[]) => {
      setUpdatingIds(new Set([...updatingIds, ...ids]));
    },
    clearUpdating: (ids?: string[]) => {
      if (ids) {
        const newSet = new Set(updatingIds);
        ids.forEach((id) => newSet.delete(id));
        setUpdatingIds(newSet);
      } else {
        setUpdatingIds(new Set());
      }
    },
  });

  return (
    <div className="flex h-screen overflow-hidden">
      <StatusPanel
        allRoles={total}
        activeRolesCount={activeCount}
        inactiveRolesCount={inactiveCount}
      />
      <div className="flex-1 flex flex-col min-w-0">
        <DataTable
          _data={roles}
          columns={columns}
          _isLoading={isLoading}
          renderToolbar={(table) => (
            <RolesTableHeader page={page} tableInstance={table} />
          )}
        />
        <Pagination
          currentPage={page}
          pageSize={limit}
          totalItems={total}
        />
      </div>
    </div>
  );
}
```

### Step 7: Create Column Definitions

```typescript
// app/(pages)/roles/_components/table/roles-table-columns.tsx
"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Badge } from "@/components/ui/badge";
import { StatusSwitch } from "@/components/ui/status-switch";
import type { Role } from "@/types/roles";

interface ColumnsProps {
  updatingIds: Set<string>;
  mutate: () => void;
  markUpdating: (ids: string[]) => void;
  clearUpdating: (ids?: string[]) => void;
}

export function createRolesTableColumns({
  updatingIds,
  mutate,
  markUpdating,
  clearUpdating,
}: ColumnsProps): ColumnDef<Role>[] {
  return [
    {
      id: "select",
      header: ({ table }) => (
        <input
          type="checkbox"
          checked={table.getIsAllPageRowsSelected()}
          onChange={(e) => table.toggleAllPageRowsSelected(e.target.checked)}
        />
      ),
      cell: ({ row }) => (
        <input
          type="checkbox"
          checked={row.getIsSelected()}
          onChange={(e) => row.toggleSelected(e.target.checked)}
        />
      ),
      size: 50,
    },
    {
      accessorKey: "name",
      header: "Name",
      cell: (info) => info.getValue(),
    },
    {
      id: "isActive",
      header: "Status",
      cell: ({ row }) => (
        <StatusSwitch
          checked={row.original.isActive}
          onToggle={async () => {
            markUpdating([row.original.id]);
            try {
              // Call API to toggle status
              await toggleRoleStatus(row.original.id, !row.original.isActive);
              mutate();
              clearUpdating([row.original.id]);
            } catch {
              clearUpdating([row.original.id]);
            }
          }}
        />
      ),
      size: 100,
    },
  ];
}
```

---

## Language Implementation

### 1. Locale File Structure

Create translations in `/locales/[lang].json`:

```json
// locales/en.json
{
  "roles": {
    "pageTitle": "Role Management",
    "searchPlaceholder": "Search roles...",
    "addRole": "Add Role",
    "addRoleSuccess": "Role created successfully",
    "addRoleFailed": "Failed to create role",
    "columns": {
      "name": "Name",
      "description": "Description",
      "status": "Status",
      "actions": "Actions"
    },
    "add": {
      "title": "Add Role",
      "description": "Create a new role",
      "name": "Name",
      "namePlaceholder": "Enter role name",
      "create": "Create",
      "cancel": "Cancel"
    },
    "edit": {
      "title": "Edit Role",
      "saveChanges": "Save Changes"
    },
    "view": {
      "title": "Role Details"
    },
    "toast": {
      "updateSuccess": "Role updated successfully",
      "updateFailed": "Failed to update role"
    }
  }
}
```

```json
// locales/ar.json
{
  "roles": {
    "pageTitle": "إدارة الأدوار",
    "searchPlaceholder": "بحث عن الأدوار...",
    "addRole": "إضافة دور",
    "addRoleSuccess": "تم إنشاء الدور بنجاح",
    "addRoleFailed": "فشل إنشاء الدور",
    "columns": {
      "name": "الاسم",
      "description": "الوصف",
      "status": "الحالة",
      "actions": "الإجراءات"
    }
  }
}
```

### 2. Using Translations in Components

```typescript
"use client";

import { useLanguage, translate } from "@/hooks/use-language";

export function RoleComponent() {
  const { t, language, dir } = useLanguage();
  const isRtl = dir === 'rtl';

  // Access nested translations
  const rolesT = (t as Record<string, unknown>).roles as Record<string, unknown>;
  const i18n = (rolesT?.add as Record<string, unknown>) || {};
  const columnsI18n = (rolesT?.columns as Record<string, unknown>) || {};

  return (
    <div className={isRtl ? 'flex-row-reverse' : ''}>
      <h1>{translate(t, 'roles.pageTitle')}</h1>
      <input
        placeholder={translate(t, 'roles.searchPlaceholder')}
      />
      <button>{(i18n.create as string) || "Create"}</button>
    </div>
  );
}
```

### 3. RTL Support Pattern

Always apply RTL-aware classes:

```typescript
const { dir } = useLanguage();
const isRtl = dir === 'rtl';

// Flex containers
className={`flex items-center gap-2 ${isRtl ? 'flex-row-reverse' : ''}`}

// Icons with spacing
<Icon className={`w-4 h-4 ${isRtl ? 'ml-2' : 'mr-2'}`} />

// Sheet/Modal side
<SheetContent side={isRtl ? "left" : "right"}>

// Text alignment (for paragraphs, descriptions)
<p className={isRtl ? 'text-right' : 'text-left'}>
```

### 4. Bilingual Data Display

For data with both English and Arabic:

```typescript
const getDisplayName = (item: { nameEn?: string; nameAr?: string; name?: string }) => {
  if (language === 'ar' && item.nameAr) {
    return item.nameAr;
  }
  if (language === 'en' && item.nameEn) {
    return item.nameEn;
  }
  return item.name || translate(t, 'common.noData');
};
```

---

## Component Patterns

### Modal/Sheet Pattern

```typescript
// components/modal/add-role-sheet.tsx
"use client";

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { useLanguage } from "@/hooks/use-language";

interface AddRoleSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (data: RoleCreate) => Promise<void>;
}

export function AddRoleSheet({ open, onOpenChange, onSave }: AddRoleSheetProps) {
  const { t, language, dir } = useLanguage();
  const isRtl = dir === 'rtl';
  const [formData, setFormData] = useState({ name: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      await onSave(formData);
      onOpenChange(false);
    } catch (error) {
      // Handle error
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side={isRtl ? "left" : "right"}>
        <SheetHeader>
          <SheetTitle className={isRtl ? 'flex-row-reverse' : ''}>
            {translate(t, 'roles.add.title')}
          </SheetTitle>
          <SheetDescription>
            {translate(t, 'roles.add.description')}
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-4 py-4">
          <input
            value={formData.name}
            onChange={(e) => setFormData({ name: e.target.value })}
            placeholder={translate(t, 'roles.add.namePlaceholder')}
          />
        </div>

        <SheetFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {translate(t, 'roles.add.create')}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
```

### Status Switch Pattern

```typescript
import { StatusSwitch } from "@/components/ui/status-switch";
import { toggleRoleStatus } from "@/lib/api/roles";

<StatusSwitch
  checked={role.isActive}
  onToggle={async () => {
    markUpdating([role.id]);
    try {
      await toggleRoleStatus(role.id, !role.isActive);
      mutate(); // Revalidate SWR cache
      clearUpdating([role.id]);
    } catch (error) {
      clearUpdating([role.id]);
      toast.error(translate(t, 'roles.toast.updateFailed'));
    }
  }}
  title={role.isActive ? "Deactivate Role" : "Activate Role"}
  description={`Are you sure you want to ${role.isActive ? 'deactivate' : 'activate'} this role?`}
  size="sm"
/>
```

### URL State Management Pattern

```typescript
import { useQueryState, parseAsInteger, parseAsString } from "nuqs";

// For pagination
const [page, setPage] = useQueryState("page", parseAsInteger.withDefault(1));
const [limit, setLimit] = useQueryState("limit", parseAsInteger.withDefault(10));

// For search
const [search, setSearch] = useQueryState("search", parseAsString.withDefault(""));

// For filters
const [isActive, setIsActive] = useQueryState("is_active", parseAsString);

// Update URL
await setPage(2); // URL becomes ?page=2
await setSearch("admin"); // URL becomes ?page=2&search=admin
```

---

## Styling Guidelines

### 1. No Border Radius
❌ **NEVER use:**
- `rounded`, `rounded-md`, `rounded-lg`, `rounded-xl`, etc.

✅ **For circles ONLY:**
- `rounded-full` (for status circles, avatars)

### 2. Consistent Spacing
- Use Tailwind spacing scale: `gap-2`, `gap-4`, `p-4`, `py-6`, etc.
- Maintain consistent spacing across similar components

### 3. Color Usage
- Primary actions: `bg-primary text-primary-foreground`
- Destructive: `bg-destructive text-destructive-foreground`
- Muted text: `text-muted-foreground`
- Borders: `border-border`
- Cards: `bg-card`

### 4. Responsive Design
```typescript
// Mobile-first approach
className="flex flex-col sm:flex-row gap-4"
className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"
```

### 5. RTL-Aware Layouts
```typescript
// Always use flex-row-reverse for RTL
className={`flex ${isRtl ? 'flex-row-reverse' : ''}`}

// Icon positioning
className={`icon ${isRtl ? 'ml-2' : 'mr-2'}`}

// Text direction handled by dir="rtl" on <html>
```

---

## Common Pitfalls

### ❌ Pitfall 1: Hardcoded Strings
```typescript
// BAD
<button>Add User</button>
<span>Loading...</span>
```

```typescript
// GOOD
<button>{translate(t, 'users.addUser')}</button>
<span>{translate(t, 'common.loading')}</span>
```

### ❌ Pitfall 2: Ignoring RTL
```typescript
// BAD
<div className="flex items-center gap-2">
  <Icon className="mr-2" />
  <span>Text</span>
</div>
```

```typescript
// GOOD
<div className={`flex items-center gap-2 ${isRtl ? 'flex-row-reverse' : ''}`}>
  <Icon className={isRtl ? 'ml-2' : 'mr-2'} />
  <span>Text</span>
</div>
```

### ❌ Pitfall 3: Using rounded classes (except rounded-full)
```typescript
// BAD
<div className="rounded-lg border p-4">
```

```typescript
// GOOD
<div className="border p-4">
// OR for circles:
<div className="rounded-full w-12 h-12">
```

### ❌ Pitfall 4: Not Excluding Super Admins
```typescript
// BAD - Backend query
query = select(User).where(User.is_active == True)
```

```typescript
// GOOD
query = select(User).where(
  User.is_active == True,
  User.is_super_admin == False
)
```

### ❌ Pitfall 5: Forgetting SWR Revalidation
```typescript
// BAD
const updateUser = async () => {
  await apiCall();
  // Data doesn't update!
};
```

```typescript
// GOOD
const updateUser = async () => {
  await apiCall();
  mutate(); // Revalidate SWR cache
};
```

### ❌ Pitfall 6: Direct State Mutation
```typescript
// BAD
updatingIds.add(id); // Mutating Set directly
```

```typescript
// GOOD
setUpdatingIds(new Set([...updatingIds, id]));
```

---

## Quick Checklist

When creating a new page, verify:

- [ ] Server component fetches initial data
- [ ] SWR configured with fallbackData
- [ ] All strings use translations (no hardcoded text)
- [ ] RTL support applied to all flex containers
- [ ] Icon spacing uses `isRtl ? 'ml-2' : 'mr-2'`
- [ ] Sheet/Modal uses `side={isRtl ? "left" : "right"}`
- [ ] No `rounded-*` classes (except `rounded-full` for circles)
- [ ] Super admins excluded from queries
- [ ] URL state management with nuqs
- [ ] Proper error handling with toast notifications
- [ ] TypeScript types defined
- [ ] Loading states handled
- [ ] Empty states handled with translations
- [ ] Confirmation dialogs for destructive actions
- [ ] Accessibility: proper labels, aria-attributes

---

## Example: Complete Minimal Page

Here's a minimal working example:

```typescript
// app/(pages)/minimal/page.tsx
import { getItems } from "@/lib/actions/items.actions";
import ItemsTable from "./_components/table/items-table";

export default async function MinimalPage({ searchParams }: {
  searchParams: Promise<{ page?: string; limit?: string }>
}) {
  const params = await searchParams;
  const page = Number(params.page) || 1;
  const limit = Number(params.limit) || 10;
  const items = await getItems({ limit, skip: (page - 1) * limit });

  return <ItemsTable initialData={items} />;
}
```

```typescript
// app/(pages)/minimal/_components/table/items-table.tsx
"use client";

import { DataTable } from "@/components/data-table";
import { Pagination } from "@/components/data-table";
import { useLanguage, translate } from "@/hooks/use-language";
import useSWR from "swr";

export default function ItemsTable({ initialData }) {
  const { t } = useLanguage();
  const { data } = useSWR("/api/items", fetcher, { fallbackData: initialData });

  const columns = [
    {
      accessorKey: "name",
      header: translate(t, 'items.columns.name'),
    },
  ];

  return (
    <div className="flex flex-col h-screen">
      <DataTable _data={data.items} columns={columns} />
      <Pagination totalItems={data.total} />
    </div>
  );
}
```

---

## Summary

This guide covers the complete pattern for creating a data management page:

1. **Server Component** → Fetch initial data
2. **Client Component** → SWR for client updates
3. **Context Provider** → Share data between components
4. **URL State** → Manage filters and pagination
5. **i18n** → Full internationalization with RTL support
6. **Modals** → Add/Edit/View with proper translations
7. **Styling** → No border-radius (except circles), RTL-aware

Follow this pattern for consistent, maintainable, and fully internationalized pages.
