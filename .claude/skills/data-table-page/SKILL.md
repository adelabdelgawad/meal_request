---
name: data-table-page
description: |
  Build admin/CRUD data table pages with server-side fetching, SWR caching, and optimistic mutations.
  Use when creating table pages, implementing CRUD operations, handling data mutations, or working with
  pagination, filters, and bulk operations. Covers the complete pattern from API to UI.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# Data Table Page Skill

## Overview

This skill teaches how to build production-grade data table pages following the established patterns in this codebase. The architecture combines:

- **Server-side data fetching** (Next.js Server Components)
- **Client-side caching** (SWR with optimistic updates)
- **URL state management** (nuqs for pagination/filters)
- **Context API** (for CRUD actions propagation)
- **TanStack Table** (for table rendering)

> **CRITICAL**: Always follow existing patterns. Do not introduce new state management libraries or data fetching approaches.

## When to Use This Skill

Activate when request involves:

- Creating a new data table page
- Adding CRUD operations to a table
- Implementing server-side data fetching
- Setting up SWR caching and mutations
- Handling optimistic UI updates
- Adding pagination, search, or filters
- Creating column definitions
- Implementing bulk operations
- Building row action menus
- Creating add/edit/view sheets/modals

## Quick Reference

### Page Structure (Reference: Users Page)

```
app/(pages)/{feature}/
├── page.tsx                    # Server component - data fetching
├── _components/
│   ├── table/
│   │   ├── {feature}-table.tsx        # SWR setup + context provider
│   │   ├── {feature}-table-body.tsx   # DataTable + toolbars
│   │   ├── {feature}-table-columns.tsx # Column definitions
│   │   ├── {feature}-table-header.tsx  # Search, export, print
│   │   └── {feature}-table-controller.tsx # Bulk actions
│   ├── actions/
│   │   ├── actions-menu.tsx           # Row action buttons
│   │   └── add-{item}-button.tsx      # Add button
│   ├── filters/                       # Filter components
│   ├── sidebar/
│   │   └── status-panel.tsx           # Summary + filters sidebar
│   └── modal/
│       ├── add-{item}-sheet.tsx       # Create form
│       ├── edit-{item}-sheet.tsx      # Update form
│       └── view-{item}-sheet.tsx      # Read-only view
└── context/
    └── {feature}-actions-context.tsx  # CRUD actions context
```

### Shared Components

| Component | Path | Purpose |
|-----------|------|---------|
| DataTable | `components/data-table/table/data-table.tsx` | TanStack Table wrapper |
| TableHeader | `components/data-table/table/table-header.tsx` | Search + export bar |
| TableController | `components/data-table/table/table-controller.tsx` | Bulk actions bar |
| Pagination | `components/data-table/table/pagination.tsx` | URL-synced pagination |
| SearchInput | `components/data-table/controls/search-input.tsx` | Debounced search |
| ExportButton | `components/data-table/actions/export-button.tsx` | CSV/Excel export |

### API Layer Files

| Type | Path Pattern |
|------|--------------|
| Server Actions | `lib/actions/{feature}.actions.ts` |
| Client API | `lib/api/{feature}.ts` |
| Types | `types/{feature}.ts` |

## Core Data Flow

```
1. page.tsx (Server)
   ↓ Fetch initial data with server actions
   ↓ Pass to client component as initialData

2. {feature}-table.tsx (Client)
   ↓ SWR hook with fallbackData: initialData
   ↓ Define updateItems() for cache mutations
   ↓ Wrap children in ContextProvider

3. Column definitions
   ↓ Receive callbacks: updateItems, markUpdating, clearUpdating
   ↓ Call API → Update cache → Show toast

4. User interaction
   ↓ markUpdating([id]) → API call → updateItems([result]) → clearUpdating()
```

## Key Patterns Summary

### 1. Server-Side Fetching (page.tsx)
```typescript
export default async function Page({ searchParams }) {
  const data = await getData(limit, skip, filters);
  return <Table initialData={data} />;
}
```

### 2. SWR Setup (table.tsx)
```typescript
const { data, mutate } = useSWR(apiUrl, fetcher, {
  fallbackData: initialData,
  keepPreviousData: true,
  revalidateOnMount: false,
});
```

### 3. Cache Update Function
```typescript
const updateItems = async (updatedItems) => {
  await mutate((current) => ({
    ...current,
    items: current.items.map(item =>
      updatedMap.has(item.id) ? updatedMap.get(item.id) : item
    ),
  }), { revalidate: false });
};
```

### 4. Mutation Pattern
```typescript
markUpdating([id]);
try {
  const result = await apiCall(id, data);
  await updateItems([result]);
  toast.success(message);
} finally {
  clearUpdating([id]);
}
```

For complete patterns, see [PATTERNS.md](PATTERNS.md).

## Allowed Operations

**DO:**
- Create new table pages following the users page structure
- Add CRUD operations with optimistic updates
- Extend shared components for feature-specific needs
- Add new column definitions with callbacks
- Create context providers for actions
- Add server actions and client API functions

**DON'T:**
- Bypass SWR for data fetching
- Use useState for server data (use SWR)
- Call APIs directly from column cells without proper error handling
- Skip the context pattern for shared actions
- Create new pagination components (use shared Pagination)

## Validation Checklist

Before completing data table work:

- [ ] Server component fetches initial data
- [ ] SWR uses fallbackData from server
- [ ] updateItems function updates cache correctly
- [ ] Mutations follow markUpdating → API → updateItems → clearUpdating
- [ ] Toast notifications on success/error
- [ ] Loading states show during operations
- [ ] URL state works for pagination/filters
- [ ] Context provides actions to nested components
- [ ] Types defined in types/{feature}.ts

## Additional Resources

- [REFERENCE.md](REFERENCE.md) - Complete API and component reference
- [EXAMPLES.md](EXAMPLES.md) - Full code examples for all patterns
- [PATTERNS.md](PATTERNS.md) - Critical implementation patterns
- [MODULES.md](MODULES.md) - Complete file inventory

## Trigger Phrases

- "data table", "table page", "CRUD page"
- "server-side fetching", "SWR", "useSWR"
- "mutations", "updateUsers", "updateItems"
- "optimistic update", "cache invalidation"
- "column definitions", "createColumns"
- "row actions", "bulk operations"
- "pagination", "filters", "search"
- "add sheet", "edit sheet", "view sheet"
- "context provider", "actions context"
