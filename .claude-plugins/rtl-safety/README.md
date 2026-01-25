# RTL Layout Safety Plugin

Checks React/TSX components for common RTL (Right-to-Left) layout issues that break Arabic layouts.

## Why This Matters

Arabic text reads right-to-left, which affects:
- Text alignment
- Icon positions
- Margins and padding
- Borders and rounded corners
- Sheet/drawer opening direction

Without proper RTL handling, Arabic layouts appear broken or confusing.

## What It Checks

1. **Directional margins** - `ml-X`, `mr-X` without RTL variants
2. **Directional padding** - `pl-X`, `pr-X` without RTL variants
3. **Text alignment** - `text-left`, `text-right` without RTL variants
4. **Icon positioning** - Icons in flex containers without gap or RTL handling
5. **Sheet/Drawer side** - Fixed side without `isRtl` check
6. **Directional borders** - `border-l-X`, `border-r-X` without RTL variants
7. **Directional corners** - `rounded-l-X`, `rounded-r-X` without RTL variants

## RTL-Safe Alternatives

### Logical CSS Properties (Preferred)

| Physical | Logical | Description |
|----------|---------|-------------|
| `ml-X` | `ms-X` | Margin start |
| `mr-X` | `me-X` | Margin end |
| `pl-X` | `ps-X` | Padding start |
| `pr-X` | `pe-X` | Padding end |
| `text-left` | `text-start` | Text align start |
| `text-right` | `text-end` | Text align end |
| `border-l` | `border-s` | Border start |
| `border-r` | `border-e` | Border end |

### RTL Variants

```tsx
// Margins
<Icon className="mr-2 rtl:mr-0 rtl:ml-2" />

// Flex direction
<div className="flex flex-row rtl:flex-row-reverse">

// Icon rotation
<ChevronRightIcon className="rtl:rotate-180" />

// Sheet side
<Sheet side={isRtl ? "left" : "right"}>
```

### Gap (Best for Icon + Text)

```tsx
// Better than margins - works for both directions
<div className="flex items-center gap-2">
  <Icon />
  <span>Text</span>
</div>
```

## Examples

### Bad (Breaks in RTL)

```tsx
// Icon always on left
<div className="flex items-center">
  <SearchIcon className="mr-2" />
  <span>Search</span>
</div>

// Text always left-aligned
<p className="text-left">Content</p>

// Sheet always from right
<Sheet side="right">
```

### Good (RTL-Safe)

```tsx
// Gap works for both directions
<div className="flex items-center gap-2">
  <SearchIcon />
  <span>Search</span>
</div>

// Uses logical property
<p className="text-start">Content</p>

// Respects RTL direction
<Sheet side={isRtl ? "left" : "right"}>
```

## Hook Behavior

- **Type:** PostToolUse (advisory)
- **Trigger:** Write or Edit to `*.tsx` files in `my-app/`
- **Action:** Prints warning message, does not block
- **Limit:** Shows up to 5 unique warnings per file
