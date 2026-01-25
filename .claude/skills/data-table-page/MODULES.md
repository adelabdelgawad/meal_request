# Data Table Page Module Inventory

Complete inventory of all files related to data table pages.

## Reference Implementation: Users Page

### Page Structure

```
src/my-app/app/(pages)/users/
├── page.tsx                                    # Server component entry
├── _components/
│   ├── table/
│   │   ├── users-table.tsx                    # SWR + context setup
│   │   ├── users-table-body.tsx               # DataTable rendering
│   │   ├── users-table-columns.tsx            # Column definitions
│   │   ├── users-table-header.tsx             # Search/export bar
│   │   ├── users-table-controller.tsx         # Bulk actions bar
│   │   └── users-table-actions.tsx            # Bulk action handlers
│   ├── actions/
│   │   ├── actions-menu.tsx                   # Row action dropdown
│   │   └── add-user-button.tsx                # Add user button
│   ├── filters/
│   │   ├── role-filter.tsx                    # Role dropdown filter
│   │   ├── role-status-filter.tsx             # Role status filter
│   │   └── user-source-filter.tsx             # User source filter
│   ├── sidebar/
│   │   └── status-panel.tsx                   # Summary + filters
│   ├── modal/
│   │   ├── add-user-sheet.tsx                 # Create user form
│   │   ├── edit-user-sheet.tsx                # Edit user form
│   │   ├── view-user-sheet.tsx                # Read-only view
│   │   ├── department-assignment-sheet.tsx    # Dept assignment
│   │   └── override-status-dialog.tsx         # Override dialog
│   ├── user-source-badge.tsx                  # Source badge
│   └── user-override-indicator.tsx            # Override indicator
└── context/
    └── users-actions-context.tsx              # CRUD context
```

### File Details

| File | Purpose | Key Exports |
|------|---------|-------------|
| `page.tsx` | Server-side data fetching | `UsersPage` (default) |
| `users-table.tsx` | SWR setup, updateUsers, context provider | `UsersTable` (default) |
| `users-table-body.tsx` | DataTable with toolbars | `UsersTableBody` (default) |
| `users-table-columns.tsx` | Column definitions factory | `createUsersTableColumns` |
| `users-table-header.tsx` | Search + export bar | `UsersTableHeader` |
| `users-table-controller.tsx` | Bulk actions bar | `UsersTableController` |
| `users-table-actions.tsx` | Bulk enable/disable handlers | `useUsersTableActions` |
| `actions-menu.tsx` | Row action dropdown | `ActionsMenu` |
| `add-user-sheet.tsx` | Create form in sheet | `AddUserSheet` |
| `edit-user-sheet.tsx` | Edit form in sheet | `EditUserSheet` |
| `view-user-sheet.tsx` | Read-only details sheet | `ViewUserSheet` |
| `users-actions-context.tsx` | CRUD actions context | `UsersProvider`, `useUsersContext`, `useUsersActions` |

---

## Shared Data Table Components

### Path: `src/my-app/components/data-table/`

```
components/data-table/
├── table/
│   ├── data-table.tsx                         # Core table wrapper
│   ├── data-table-bar.tsx                     # Flexible bar layout
│   ├── table-header.tsx                       # Header bar template
│   ├── table-controller.tsx                   # Controller bar template
│   └── pagination.tsx                         # URL-synced pagination
├── controls/
│   ├── search-input.tsx                       # Debounced search
│   ├── column-toggle-button.tsx               # Column visibility
│   └── refresh-button.tsx                     # Manual refresh
├── actions/
│   ├── export-button.tsx                      # CSV/Excel export
│   ├── export-all-button.tsx                  # Export all pages
│   ├── print-button.tsx                       # Print functionality
│   ├── enable-button.tsx                      # Bulk enable
│   ├── disable-button.tsx                     # Bulk disable
│   └── selection-display.tsx                  # Selected count
├── sidebar/
│   └── status-panel.tsx                       # Sidebar template
├── mobile/
│   └── data-card.tsx                          # Mobile card view
├── ui/
│   ├── button.tsx                             # Table button style
│   ├── status-badge.tsx                       # Status badge
│   └── status-circle.tsx                      # Status indicator
└── index.tsx                                  # Public exports
```

### Component Details

| Component | File | Purpose |
|-----------|------|---------|
| `DataTable` | `table/data-table.tsx` | TanStack Table wrapper |
| `Pagination` | `table/pagination.tsx` | nuqs-based pagination |
| `TableHeader` | `table/table-header.tsx` | Search/export/print bar |
| `TableController` | `table/table-controller.tsx` | Bulk actions bar |
| `DataTableBar` | `table/data-table-bar.tsx` | Left/middle/right layout |
| `SearchInput` | `controls/search-input.tsx` | Debounced URL search |
| `ColumnToggleButton` | `controls/column-toggle-button.tsx` | Show/hide columns |
| `RefreshButton` | `controls/refresh-button.tsx` | Force refresh |
| `ExportButton` | `actions/export-button.tsx` | Page export |
| `ExportAllButton` | `actions/export-all-button.tsx` | All data export |
| `PrintButton` | `actions/print-button.tsx` | Print table |
| `EnableButton` | `actions/enable-button.tsx` | Bulk enable |
| `DisableButton` | `actions/disable-button.tsx` | Bulk disable |
| `SelectionDisplay` | `actions/selection-display.tsx` | Show selected count |
| `StatusPanel` | `sidebar/status-panel.tsx` | Summary sidebar |
| `DataCard` | `mobile/data-card.tsx` | Mobile card |
| `StatusBadge` | `ui/status-badge.tsx` | Active/inactive badge |

---

## API Layer Files

### Server Actions

**Path:** `src/my-app/lib/actions/`

| File | Exports | Purpose |
|------|---------|---------|
| `users.actions.ts` | `getUsers`, `getUserById`, `getDomainUsers` | User data fetching |
| `roles.actions.ts` | `getRoles`, `getRoleById` | Role data fetching |
| `departments.actions.ts` | `getAllDepartments` | Department data |

### Client API

**Path:** `src/my-app/lib/api/`

| File | Exports | Purpose |
|------|---------|---------|
| `users.ts` | `toggleUserStatus`, `updateUser`, `createUser`, `deleteUser`, `bulkUpdateUserStatus`, `updateUserRoles`, `markUserAsManual`, `overrideUserStatus`, `getUserSources` | User mutations |
| `roles.ts` | `createRole`, `updateRole`, `deleteRole` | Role mutations |

### HTTP Clients

**Path:** `src/my-app/lib/http/`

| File | Exports | Purpose |
|------|---------|---------|
| `axios-server.ts` | `serverApi` | Server-side requests |
| `axios-client.ts` | `clientApi` | Client-side requests |

---

## Type Definitions

### Path: `src/my-app/types/`

| File | Key Types | Purpose |
|------|-----------|---------|
| `users.ts` | `UserResponse`, `UserWithRolesResponse`, `SettingUsersResponse`, `UserCreate`, `UserUpdate`, `AuthUserResponse`, `UserSourceMetadata` | User types |
| `roles.ts` | `RoleResponse`, `RoleCreate`, `RoleUpdate` | Role types |

### User Types Detail

```typescript
// types/users.ts
interface UserResponse {
  id: string;
  username: string;
  email: string | null;
  fullName: string | null;
  title: string | null;
  isActive: boolean;
  isBlocked: boolean;
  userSource: 'hris' | 'manual';
  userSourceMetadata?: UserSourceMetadata;
  statusOverride: boolean;
  overrideReason?: string | null;
}

interface UserWithRolesResponse extends UserResponse {
  roles: string[];
  roleIds: number[];
  assignedDepartmentCount?: number;
}

interface SettingUsersResponse {
  users: UserWithRolesResponse[];
  total: number;
  activeCount: number;
  inactiveCount: number;
  roleOptions: SimpleRole[];
}
```

---

## Internationalization

### Path: `src/my-app/locales/`

| File | Purpose |
|------|---------|
| `en/table.json` | English table translations |
| `ar/table.json` | Arabic table translations |
| `en/users.json` | English users page translations |
| `ar/users.json` | Arabic users page translations |

### Translation Keys Structure

```json
{
  "table": {
    "search": "Search...",
    "export": "Export",
    "print": "Print",
    "noDataAvailable": "No data available",
    "columns": "Columns",
    "selected": "selected"
  },
  "users": {
    "title": "Users",
    "add": "Add User",
    "edit": {
      "title": "Edit User",
      "save": "Save Changes",
      "cancel": "Cancel"
    },
    "columns": {
      "username": "Username",
      "fullName": "Full Name",
      "email": "Email",
      "isActive": "Active",
      "roles": "Roles"
    }
  }
}
```

---

## Hooks

### Path: `src/my-app/hooks/`

| File | Exports | Purpose |
|------|---------|---------|
| `use-language.ts` | `useLanguage` | Language, translations, direction |
| `use-debounce.ts` | `useDebounce` | Debounce values |

---

## UI Components Used

### Path: `src/my-app/components/ui/`

| Component | File | Purpose |
|-----------|------|---------|
| `Sheet` | `sheet.tsx` | Side panel container |
| `Button` | `button.tsx` | Button variants |
| `Input` | `input.tsx` | Form input |
| `Label` | `label.tsx` | Form label |
| `Badge` | `badge.tsx` | Badges/tags |
| `AlertDialog` | `alert-dialog.tsx` | Confirmation dialogs |
| `StatusSwitch` | `status-switch.tsx` | Toggle with confirmation |
| `custom-toast` | `custom-toast.ts` | Toast notifications |

---

## Where to Add New Code

### Creating a New Data Table Page

1. **Page Component**: `app/(pages)/{feature}/page.tsx`
2. **Table Components**: `app/(pages)/{feature}/_components/table/`
3. **Modal Components**: `app/(pages)/{feature}/_components/modal/`
4. **Context**: `app/(pages)/{feature}/context/{feature}-actions-context.tsx`
5. **Server Actions**: `lib/actions/{feature}.actions.ts`
6. **Client API**: `lib/api/{feature}.ts`
7. **Types**: `types/{feature}.ts`
8. **Translations**: `locales/{lang}/{feature}.json`

### Adding to Existing Page

| Change | File to Modify |
|--------|----------------|
| New column | `_components/table/{feature}-table-columns.tsx` |
| New filter | `_components/filters/` (new file) |
| New action | `_components/actions/actions-menu.tsx` |
| New bulk operation | `_components/table/{feature}-table-actions.tsx` |
| New modal | `_components/modal/` (new file) |
| New context action | `context/{feature}-actions-context.tsx` |
| New API mutation | `lib/api/{feature}.ts` |

---

## Dependency Graph

```
page.tsx (Server)
    ├── lib/actions/{feature}.actions.ts  (data fetching)
    └── _components/table/{feature}-table.tsx (Client)
            ├── useSWR (caching)
            ├── useState (updatingIds)
            ├── context/{feature}-actions-context.tsx
            │       └── actions object (onToggle, update, refresh)
            └── {feature}-table-body.tsx
                    ├── components/data-table/table/data-table.tsx
                    ├── {feature}-table-columns.tsx
                    │       └── lib/api/{feature}.ts (mutations)
                    ├── {feature}-table-header.tsx
                    │       ├── SearchInput
                    │       ├── ExportButton
                    │       └── PrintButton
                    └── {feature}-table-controller.tsx
                            ├── EnableButton
                            ├── DisableButton
                            └── ColumnToggleButton
```

---

## File Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Page | `page.tsx` | `app/(pages)/users/page.tsx` |
| Table wrapper | `{feature}-table.tsx` | `users-table.tsx` |
| Table body | `{feature}-table-body.tsx` | `users-table-body.tsx` |
| Columns | `{feature}-table-columns.tsx` | `users-table-columns.tsx` |
| Context | `{feature}-actions-context.tsx` | `users-actions-context.tsx` |
| Server actions | `{feature}.actions.ts` | `users.actions.ts` |
| Client API | `{feature}.ts` | `users.ts` |
| Types | `{feature}.ts` | `users.ts` |
| Modals | `{action}-{item}-sheet.tsx` | `add-user-sheet.tsx` |
