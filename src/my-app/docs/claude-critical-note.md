<!--
  CRITICAL: Append this block to your repository's claude.md or CLAUDE.md file.
  This ensures Claude Code AI understands the new architecture when working on frontend code.
-->

---

## ⚠️ CRITICAL: Frontend API Integration (camelCase Migration)

**Effective Date**: 2025-11-28
**Status**: ✅ ACTIVE - All new code MUST follow this pattern

### Overview

The backend has migrated to **camelCase JSON contract** using Pydantic v2 `CamelModel` with `alias_generator=to_camel`. All API responses now use camelCase keys instead of snake_case.

**Examples of changes**:
- `access_token` → `accessToken`
- `is_super_admin` → `isSuperAdmin`
- `created_at` → `createdAt`
- `refresh_token` → `refreshToken`
- `name_en` / `name_ar` → `nameEn` / `nameAr`

### Frontend Architecture

**DO NOT use these deprecated patterns**:
- ❌ `lib/http/axios-client.ts` (proxies to `/api/*` routes)
- ❌ `lib/api/auth.actions.ts` (uses snake_case)
- ❌ `lib/auth/token-manager.ts` (manual token refresh)
- ❌ Direct snake_case property access (e.g., `response.data.access_token`)

**ALWAYS use the new centralized modules**:
- ✅ `src/lib/api-client.ts` - Direct backend communication with `apiFetch<T>()`
- ✅ `src/lib/auth.ts` - Login, logout, session management
- ✅ `src/lib/locale.ts` - Locale switching and persistence
- ✅ `src/lib/navigation.ts` - Navigation tree fetching
- ✅ `src/lib/error-handler.ts` - Centralized error handling
- ✅ `src/types/*.types.ts` - All TypeScript interfaces with camelCase

### Key Implementation Patterns

#### 1. API Calls - Use `apiFetch<T>()`

```typescript
import { apiFetch } from '@/lib/api-client';
import type { UserInfo } from '@/types/auth.types';

// ✅ CORRECT
const user = await apiFetch<UserInfo>('/me');
console.log(user.isSuperAdmin); // camelCase

// ❌ WRONG
const response = await axios.get('/api/v1/me');
console.log(response.data.is_super_admin); // snake_case
```

**Features of `apiFetch()`**:
- Automatic `Authorization: Bearer <token>` header injection
- Automatic `Accept-Language` header based on locale cookie
- Concurrency-safe automatic token refresh on 401
- Always includes `credentials: 'include'` for cookie-based auth
- Supports both stateful (cookie) and legacy (body) token modes

#### 2. Authentication - Use `src/lib/auth.ts`

```typescript
import { login, logout, getSession } from '@/lib/auth';
import type { LoginRequest, LoginResponse } from '@/types/auth.types';

// ✅ Login
const response = await login({ username, password, scope: 'local' });
console.log(response.accessToken); // camelCase
console.log(response.user.isSuperAdmin); // camelCase

// ✅ Session validation
const session = await getSession();
console.log(session.user.id);

// ✅ Logout
await logout(); // Handles both stateful and legacy modes
```

**DO NOT**:
- Manually construct Authorization headers
- Manually refresh tokens (it's automatic in `apiFetch()`)
- Access `localStorage` directly for tokens

#### 3. Locale Management - Use `src/lib/locale.ts`

```typescript
import { getLocale, changeLocale } from '@/lib/locale';

// ✅ Get current locale
const currentLocale = getLocale(); // 'en' | 'ar'

// ✅ Change locale (persists to backend + cookie)
await changeLocale('ar'); // Auto-reloads page

// ✅ Set Accept-Language header (automatic in apiFetch)
// No manual work needed - apiFetch() reads locale cookie
```

#### 4. Navigation - Use `src/lib/navigation.ts`

```typescript
import { getNavigation } from '@/lib/navigation';
import type { NavigationResponse } from '@/types/navigation.types';

// ✅ Fetch navigation tree
const nav = await getNavigation('main');
console.log(nav.items[0].nameEn); // camelCase
console.log(nav.items[0].nameAr); // camelCase
console.log(nav.items[0].isMenuGroup); // camelCase
```

#### 5. Error Handling - Use `src/lib/error-handler.ts`

```typescript
import { handleApiError } from '@/lib/error-handler';

try {
  const data = await apiFetch('/protected-resource');
} catch (error) {
  handleApiError(error); // Shows toast, redirects on 401, etc.
}
```

### Environment Variables

Add to `.env.local`:

```env
# Backend API base URL (without /api/v1)
NEXT_PUBLIC_API_BASE_URL=http://localhost:1013/api/v1

# Enable stateful sessions (cookie-based refresh tokens)
NEXT_PUBLIC_USE_STATEFUL_SESSIONS=true

# Frontend URL (for redirects)
NEXT_PUBLIC_FRONTEND_URL=http://localhost:3000
```

### Migration Checklist

When working on existing frontend code:

1. **Replace snake_case types**:
   ```typescript
   // ❌ OLD
   interface LoginResponse { access_token: string; }

   // ✅ NEW
   import type { LoginResponse } from '@/types/auth.types';
   ```

2. **Replace axios/fetch calls**:
   ```typescript
   // ❌ OLD
   const response = await axios.get('/api/v1/users');

   // ✅ NEW
   const users = await apiFetch<User[]>('/users');
   ```

3. **Replace property access**:
   ```typescript
   // ❌ OLD
   const token = response.data.access_token;
   const isAdmin = user.is_super_admin;

   // ✅ NEW
   const token = response.accessToken;
   const isAdmin = user.isSuperAdmin;
   ```

4. **Replace manual token refresh**:
   ```typescript
   // ❌ OLD
   if (response.status === 401) {
     const newToken = await refreshAccessToken();
     // retry request...
   }

   // ✅ NEW
   // Token refresh is automatic in apiFetch() - just call it normally
   const data = await apiFetch('/protected-resource');
   ```

### Testing

**Unit Tests** (Vitest + MSW):
```bash
npm run test:unit
# See: tests/unit/api-client.test.ts
```

**E2E Tests** (Playwright):
```bash
npm run test:e2e
# See: tests/e2e/auth-flow.spec.ts
```

### Applying Patches

Minimal, safe patches for existing code are provided in `patches/`:

```bash
# Review patches first
cat patches/001-auth-actions-camelcase.patch
cat patches/002-token-manager-camelcase.patch
cat patches/003-login-route-camelcase.patch
cat patches/004-session-route-camelcase.patch

# Apply patches (from my-app directory)
git apply patches/001-auth-actions-camelcase.patch
git apply patches/002-token-manager-camelcase.patch
git apply patches/003-login-route-camelcase.patch
git apply patches/004-session-route-camelcase.patch
```

### Common Pitfalls

1. **Mixing snake_case and camelCase**: Always use camelCase for API responses
2. **Forgetting credentials**: Always use `credentials: 'include'` for cookie-based auth
3. **Manual token refresh**: Let `apiFetch()` handle it automatically
4. **Not importing types**: Always import from `@/types/*.types.ts` for type safety
5. **Locale header**: Let `apiFetch()` inject `Accept-Language` automatically

### Support

- **Documentation**: See `docs/migration-checklist.md` for detailed steps
- **PR Template**: See `docs/PR_DESCRIPTION.md` for PR format
- **Verification**: Run `./verify.sh` before committing

---

**Last Updated**: 2025-11-28
**Maintained By**: Backend Team (camelCase standardization initiative)
