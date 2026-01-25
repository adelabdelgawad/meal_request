# i18n & RTL Reference

Quick reference for internationalization and RTL support.

## File Locations

| Component | Path |
|-----------|------|
| English Translations | `src/my-app/locales/en/` |
| Arabic Translations | `src/my-app/locales/ar/` |
| Language Hook | `src/my-app/hooks/use-language.ts` |
| Language Provider | `src/my-app/providers/language-provider.tsx` |

## Logical CSS Properties

| Physical | Logical | Description |
|----------|---------|-------------|
| `ml-*` | `ms-*` | Margin start |
| `mr-*` | `me-*` | Margin end |
| `pl-*` | `ps-*` | Padding start |
| `pr-*` | `pe-*` | Padding end |
| `text-left` | `text-start` | Text align start |
| `text-right` | `text-end` | Text align end |
| `left-*` | `start-*` | Position start |
| `right-*` | `end-*` | Position end |

## RTL Tailwind Variants

```css
/* Flex direction */
flex-row rtl:flex-row-reverse

/* Margins (when logical properties not available) */
mr-2 rtl:mr-0 rtl:ml-2

/* Rotation for directional icons */
rtl:rotate-180

/* Borders */
border-l-4 rtl:border-l-0 rtl:border-r-4
rounded-l-lg rtl:rounded-l-none rtl:rounded-r-lg

/* Transforms */
translate-x-2 rtl:-translate-x-2
```

## Components Needing RTL Handling

| Component | RTL Consideration |
|-----------|-------------------|
| Sheet/Drawer | Open from opposite side |
| Chevron icons | Rotate 180 degrees |
| Progress bars | Direction property |
| Sliders | Direction property |
| Tabs | Border position |
| Breadcrumbs | Separator direction |
| Pagination | Arrow direction |

## Bilingual Field Convention

| English Field | Arabic Field |
|---------------|--------------|
| `name_en` | `name_ar` |
| `description_en` | `description_ar` |
| `title_en` | `title_ar` |
| `label_en` | `label_ar` |
| `content_en` | `content_ar` |

## Translation Key Convention

```json
{
  "page": {
    "title": "Page Title",
    "subtitle": "Page description"
  },
  "table": {
    "columnName": "Column Header"
  },
  "actions": {
    "add": "Add",
    "edit": "Edit",
    "delete": "Delete",
    "save": "Save",
    "cancel": "Cancel"
  },
  "messages": {
    "success": "Operation successful",
    "error": "An error occurred",
    "confirm": "Are you sure?"
  },
  "validation": {
    "required": "This field is required",
    "minLength": "Minimum {min} characters"
  }
}
```

## Common Arabic Translations

| English | Arabic |
|---------|--------|
| Save | حفظ |
| Cancel | إلغاء |
| Delete | حذف |
| Edit | تعديل |
| Add | إضافة |
| Search | بحث |
| Filter | تصفية |
| Active | نشط |
| Inactive | غير نشط |
| Yes | نعم |
| No | لا |
| Loading | جاري التحميل |
| Error | خطأ |
| Success | نجاح |
| Submit | إرسال |
| Close | إغلاق |
| Back | رجوع |
| Next | التالي |
| Previous | السابق |

## Hook Usage

```typescript
const { t, locale, isRtl, setLocale } = useLanguage();

// Get translation
const title = t("page.title");

// Get nested translation
const columnHeader = t("table.columnName");

// Check direction
if (isRtl) {
  // RTL-specific logic
}

// Change language
setLocale("ar");
```

## Component Patterns

### Directional Icon

```tsx
<ChevronRightIcon className={isRtl ? "rotate-180" : ""} />
```

### Sheet Side

```tsx
<Sheet side={isRtl ? "left" : "right"}>
```

### Gap Instead of Margins

```tsx
// Better than margin + RTL variant
<div className="flex items-center gap-2">
  <Icon />
  <span>Text</span>
</div>
```

### Localized Name Display

```tsx
const name = locale === "ar" ? item.nameAr : item.nameEn;
```

## Testing Checklist

- [ ] Toggle language switcher
- [ ] Check all text displays correctly
- [ ] Verify icons flip appropriately
- [ ] Check sheets open from correct side
- [ ] Verify margins/padding mirror correctly
- [ ] Test form layouts
- [ ] Check table column alignment
- [ ] Verify date/number formatting
