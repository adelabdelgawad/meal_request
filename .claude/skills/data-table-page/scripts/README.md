# Data Table Page Utility Scripts

Scripts for validating and scaffolding data table pages.

## Scripts

### scaffold-table-page.py

Generate boilerplate for a new data table page.

```bash
# Create a new products table page
python .claude/skills/data-table-page/scripts/scaffold-table-page.py products

# Specify output directory
python .claude/skills/data-table-page/scripts/scaffold-table-page.py products --output src/my-app/app/(pages)

# Preview without creating files
python .claude/skills/data-table-page/scripts/scaffold-table-page.py products --dry-run
```

**Generated Files:**
- `page.tsx` - Server component
- `_components/table/{feature}-table.tsx` - SWR wrapper
- `_components/table/{feature}-table-body.tsx` - Table body
- `_components/table/{feature}-table-columns.tsx` - Columns
- `context/{feature}-actions-context.tsx` - Context provider

### validate-table-page.py

Validate an existing data table page follows the patterns.

```bash
# Validate users page
python .claude/skills/data-table-page/scripts/validate-table-page.py src/my-app/app/(pages)/users

# Verbose output
python .claude/skills/data-table-page/scripts/validate-table-page.py src/my-app/app/(pages)/users --verbose
```

**Checks:**
- [x] page.tsx exists and is Server Component
- [x] SWR hook with correct options
- [x] updateItems function defined
- [x] Context provider wraps children
- [x] Column definitions follow pattern
- [x] Loading state tracking
- [x] Error handling

### check-swr-config.py

Check SWR configuration across all table pages.

```bash
# Check all table pages
python .claude/skills/data-table-page/scripts/check-swr-config.py

# Check specific page
python .claude/skills/data-table-page/scripts/check-swr-config.py --path src/my-app/app/(pages)/users
```

## Common Issues

### SWR Not Using fallbackData

```typescript
// ❌ Wrong
const { data } = useSWR(url, fetcher);

// ✅ Correct
const { data } = useSWR(url, fetcher, {
  fallbackData: initialData,
});
```

### Missing revalidate: false

```typescript
// ❌ Wrong - causes refetch after update
await mutate((data) => newData);

// ✅ Correct - no refetch
await mutate((data) => newData, { revalidate: false });
```

### Not Clearing Loading State on Error

```typescript
// ❌ Wrong
try {
  markUpdating([id]);
  await apiCall();
  clearUpdating([id]);  // Never called on error!
} catch (e) {
  toast.error("Failed");
}

// ✅ Correct
try {
  markUpdating([id]);
  await apiCall();
} finally {
  clearUpdating([id]);  // Always called
}
```
