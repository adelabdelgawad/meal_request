---
name: i18n-rtl-consistency
description: |
  Maintain bilingual support and RTL layout consistency across the application.
  Use when adding translations, implementing RTL-aware layouts, working with bilingual
  model fields, checking translation completeness, or converting LTR components to RTL.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# i18n & RTL Consistency

## Overview

This skill helps maintain bilingual (English/Arabic) support and RTL layout consistency:

- **Translation files** - JSON-based locale files
- **RTL layouts** - Proper mirroring for Arabic
- **Bilingual fields** - Database and API patterns
- **Locale detection** - Cookie-based persistence

> **CRITICAL**: RTL bugs are easy to introduce and hard to spot. Always test Arabic layout.

## When to Use This Skill

Activate when request involves:

- Adding new UI strings to translations
- Creating RTL-aware component layouts
- Implementing bilingual model fields
- Checking translation completeness
- Converting LTR-only components to RTL
- Working with the language switcher
- Handling locale in API responses

## Quick Reference

### Frontend Locations

| Component | Path |
|-----------|------|
| English Translations | `src/my-app/locales/en/*.json` |
| Arabic Translations | `src/my-app/locales/ar/*.json` |
| Language Hook | `src/my-app/hooks/use-language.ts` |
| Language Provider | `src/my-app/providers/language-provider.tsx` |
| Language Switcher | `src/my-app/components/language-switcher.tsx` |
| RTL Utilities | `src/my-app/lib/rtl-utils.ts` |

### Backend Locations

| Component | Path |
|-----------|------|
| Bilingual Models | `src/backend/db/models.py` |
| Locale Detection | `src/backend/utils/locale.py` |
| Localized Responses | `src/backend/api/services/*_service.py` |

## Translation File Pattern

### File Structure

```
src/my-app/locales/
├── en/
│   ├── common.json      # Shared UI strings
│   ├── navigation.json  # Menu and nav items
│   ├── users.json       # User management page
│   ├── roles.json       # Role management page
│   └── scheduler.json   # Scheduler page
└── ar/
    ├── common.json
    ├── navigation.json
    ├── users.json
    ├── roles.json
    └── scheduler.json
```

### Translation File Format

```json
// locales/en/users.json
{
  "title": "User Management",
  "subtitle": "Manage user accounts and permissions",
  "table": {
    "username": "Username",
    "fullName": "Full Name",
    "status": "Status",
    "roles": "Roles",
    "actions": "Actions"
  },
  "status": {
    "active": "Active",
    "inactive": "Inactive"
  },
  "actions": {
    "add": "Add User",
    "edit": "Edit",
    "delete": "Delete",
    "activate": "Activate",
    "deactivate": "Deactivate"
  },
  "messages": {
    "createSuccess": "User created successfully",
    "updateSuccess": "User updated successfully",
    "deleteConfirm": "Are you sure you want to delete this user?"
  }
}
```

```json
// locales/ar/users.json
{
  "title": "إدارة المستخدمين",
  "subtitle": "إدارة حسابات المستخدمين والصلاحيات",
  "table": {
    "username": "اسم المستخدم",
    "fullName": "الاسم الكامل",
    "status": "الحالة",
    "roles": "الأدوار",
    "actions": "الإجراءات"
  },
  "status": {
    "active": "نشط",
    "inactive": "غير نشط"
  },
  "actions": {
    "add": "إضافة مستخدم",
    "edit": "تعديل",
    "delete": "حذف",
    "activate": "تفعيل",
    "deactivate": "إلغاء التفعيل"
  },
  "messages": {
    "createSuccess": "تم إنشاء المستخدم بنجاح",
    "updateSuccess": "تم تحديث المستخدم بنجاح",
    "deleteConfirm": "هل أنت متأكد من حذف هذا المستخدم؟"
  }
}
```

## Language Hook Pattern

```typescript
// hooks/use-language.ts
"use client";

import { useCallback, useMemo } from "react";
import { useLocale } from "@/providers/language-provider";
import enCommon from "@/locales/en/common.json";
import arCommon from "@/locales/ar/common.json";
// Import other locale files...

type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export function useLanguage() {
  const { locale, setLocale, isRtl } = useLocale();

  // Merge all translation files
  const translations = useMemo(() => {
    const en = { common: enCommon, /* other namespaces */ };
    const ar = { common: arCommon, /* other namespaces */ };
    return locale === "ar" ? ar : en;
  }, [locale]);

  // Translation function with nested key support
  const t = useCallback(
    (key: string, defaultValue?: string): string => {
      const keys = key.split(".");
      let value: any = translations;

      for (const k of keys) {
        value = value?.[k];
        if (value === undefined) break;
      }

      return typeof value === "string" ? value : defaultValue ?? key;
    },
    [translations]
  );

  return {
    locale,
    setLocale,
    isRtl,
    t,
    translations,
  };
}

// Usage
function UserPage() {
  const { t, isRtl, locale } = useLanguage();

  return (
    <div dir={isRtl ? "rtl" : "ltr"}>
      <h1>{t("users.title")}</h1>
      <p>{t("users.subtitle")}</p>
    </div>
  );
}
```

## RTL Layout Patterns

### Flex Direction

```tsx
// ❌ WRONG - Fixed direction
<div className="flex flex-row">
  <Icon />
  <span>Text</span>
</div>

// ✅ CORRECT - RTL-aware
<div className="flex flex-row rtl:flex-row-reverse">
  <Icon />
  <span>Text</span>
</div>

// Or use gap instead of margins
<div className="flex items-center gap-2">
  <Icon />
  <span>Text</span>
</div>
```

### Margins and Padding

```tsx
// ❌ WRONG - Fixed margins
<Icon className="mr-2" />  // Always right margin

// ✅ CORRECT - RTL-aware
<Icon className="mr-2 rtl:mr-0 rtl:ml-2" />  // Swaps for RTL

// Or better - use logical properties
<Icon className="me-2" />  // margin-inline-end (works for both)
```

### Text Alignment

```tsx
// ❌ WRONG - Fixed alignment
<p className="text-left">Content</p>

// ✅ CORRECT - RTL-aware
<p className="text-start">Content</p>  // Uses logical property
```

### Icons with Directional Meaning

```tsx
// Icons that should flip in RTL
const DirectionalIcon = ({ isRtl }: { isRtl: boolean }) => (
  <ChevronRightIcon className={isRtl ? "rotate-180" : ""} />
);

// Or use CSS
<ChevronRightIcon className="rtl:rotate-180" />
```

### Sheet/Modal Positioning

```tsx
// ❌ WRONG - Fixed side
<Sheet side="right">

// ✅ CORRECT - RTL-aware
<Sheet side={isRtl ? "left" : "right"}>
```

### Table Column Order

```tsx
// For tables with actions column
const columns = useMemo(() => {
  const cols = [
    { id: "name", header: t("table.name") },
    { id: "status", header: t("table.status") },
    { id: "actions", header: t("table.actions") },
  ];

  // In RTL, you might want actions on the left
  // Most tables work fine without reordering
  return cols;
}, [t]);
```

## Bilingual Field Pattern

### Database Model

```python
# db/models.py
class Role(Base):
    __tablename__ = "role"

    id = Column(Integer, primary_key=True)
    name_en = Column(String(100), nullable=False)
    name_ar = Column(String(100), nullable=False)
    description_en = Column(Text, nullable=True)
    description_ar = Column(Text, nullable=True)
```

### Pydantic Schema

```python
# api/schemas/role_schemas.py
from api.schemas._base import CamelModel

class RoleResponse(CamelModel):
    id: int
    name_en: str      # → "nameEn"
    name_ar: str      # → "nameAr"
    description_en: Optional[str]  # → "descriptionEn"
    description_ar: Optional[str]  # → "descriptionAr"
```

### TypeScript Type

```typescript
// types/role.ts
interface Role {
  id: number;
  nameEn: string;
  nameAr: string;
  descriptionEn: string | null;
  descriptionAr: string | null;
}

// Helper for localized display
function getLocalizedName(item: Role, locale: "en" | "ar"): string {
  return locale === "ar" ? item.nameAr : item.nameEn;
}
```

### Usage in Component

```tsx
function RoleList({ roles }: { roles: Role[] }) {
  const { locale } = useLanguage();

  return (
    <ul>
      {roles.map((role) => (
        <li key={role.id}>
          {locale === "ar" ? role.nameAr : role.nameEn}
        </li>
      ))}
    </ul>
  );
}
```

## Tailwind RTL Configuration

```javascript
// tailwind.config.js
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [
    // Add RTL plugin if not using built-in support
    require("tailwindcss-rtl"),
  ],
};
```

## Allowed Operations

**DO:**
- Use `me-*`, `ms-*`, `ps-*`, `pe-*` for margins/padding
- Use `text-start`, `text-end` for alignment
- Add RTL variants: `rtl:flex-row-reverse`
- Test both LTR and RTL layouts
- Create matching AR translations for all EN strings

**DON'T:**
- Use fixed `ml-*`, `mr-*` without RTL counterpart
- Use fixed `text-left`, `text-right` without RTL variant
- Forget to add Arabic translations
- Hardcode English text in components
- Assume all icons work in RTL

## Validation Checklist

Before completing i18n/RTL work:

- [ ] All UI strings in translation files
- [ ] Arabic translations match English keys
- [ ] Flex containers have RTL variants
- [ ] Margins/padding use logical properties
- [ ] Directional icons flip in RTL
- [ ] Sheets/modals open from correct side
- [ ] Text alignment uses logical properties
- [ ] Tested in both EN and AR modes

## Additional Resources

- [PATTERNS.md](PATTERNS.md) - RTL CSS patterns
- [REFERENCE.md](REFERENCE.md) - Quick reference

## Trigger Phrases

- "translation", "i18n", "localization"
- "RTL", "right-to-left", "Arabic"
- "bilingual", "name_en", "name_ar"
- "language switcher", "locale"
- "margin flip", "direction"
