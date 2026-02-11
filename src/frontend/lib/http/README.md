# HTTP Layer Architecture

This directory contains the centralized HTTP communication layer for the application, eliminating duplication and providing consistent error handling, timeouts, and response shapes across all endpoints.

## Files Overview

### 1. `http-utils.ts`
**Purpose:** Centralized utilities for HTTP communication

**Key Features:**
- `ApiResponse<T>`: Standard API response shape
- `Result<T>`: Union type for success/error results
- `getBackendUrl()`: Resolves backend URL from environment or defaults
- `normalizeError()`: Standardizes errors from various sources (Axios, FastAPI, network errors)
- `mapResponse<T>()`: Maps responses to consistent result shape
- Constants: `HTTP_TIMEOUT`, `DEFAULT_HEADERS`

**Used by:** All HTTP connectors

### 2. `axios-server.ts`
**Purpose:** Server-side HTTP communication (used in API routes and server actions)

**Key Features:**
- `serverRequest<T>()`: Core method for making requests to the backend
- `serverApi`: Convenience object with `.get()`, `.post()`, `.put()`, `.patch()`, `.delete()` methods
- Uses Axios with timeout and automatic status code validation
- Returns normalized `Result<T>` type
- Intended for Next.js API routes and server actions

**Example Usage:**
```typescript
import { serverApi } from "@/lib/http/axios-server";

// In an API route
const result = await serverApi.post("/login", { username, password });
if (result.ok) {
  return NextResponse.json({ data: result.data }, { status: 200 });
} else {
  return NextResponse.json({ error: result.message }, { status: result.status });
}
```

### 3. `axios-client.ts`
**Purpose:** Client-side HTTP communication (used in components and client hooks)

**Key Features:**
- `clientRequest<T>()`: Core method for making requests to `/api/*` routes
- `clientApi`: Convenience object with `.get()`, `.post()`, `.put()`, `.patch()`, `.delete()` methods
- Uses Axios with timeout and automatic status code validation
- Returns normalized `Result<T>` type
- Intended for browser-based client components

**Example Usage:**
```typescript
import { clientApi } from "@/lib/http/axios-client";

// In a client component
const result = await clientApi.post("/auth/login", { username, password });
if (result.ok) {
  // Handle success
} else {
  // Handle error: result.message contains user-friendly message
}
```

## Architecture Flow

### Request Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ BROWSER / CLIENT COMPONENT                                      │
│ (uses clientApi)                                                │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │ /api/auth/login (Next.js)   │
         │ (API Route)                 │
         │ (uses serverApi)            │
         └──────────────┬──────────────┘
                        │
                        ▼
         ┌──────────────────────────────────┐
         │ Backend Service (FastAPI)        │
         │ http://localhost:1013           │
         │ - /login endpoint               │
         │ - Error handling                │
         └──────────────────────────────────┘
```

## Response Normalization

### Success Response
All successful API responses are normalized to:
```typescript
{
  ok: true,
  data: any,
  status: 200
}
```

### Error Response
All error responses are normalized to:
```typescript
{
  ok: false,
  message: "User-friendly error message",
  error: "error_code",
  status: 401
}
```

## Error Handling

The `normalizeError()` function handles multiple error sources:

1. **Axios Response Errors**: Extracts status and message
2. **FastAPI HTTPException**: Reads `detail` field
3. **Network Errors**: Standard error message with appropriate status
4. **Timeout Errors**: Returns 504 status with timeout message
5. **Unknown Errors**: Fallback to generic error message

## Usage Examples

### Server-Side (API Route)

```typescript
import { serverApi } from "@/lib/http/axios-server";
import { NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const body = await request.json();

  // Call backend with automatic error handling
  const result = await serverApi.post("/login", body);

  return NextResponse.json(
    {
      ok: result.ok,
      message: result.message,
      data: result.data,
    },
    { status: result.status }
  );
}
```

### Client-Side (Component)

```typescript
import { clientApi } from "@/lib/http/axios-client";
import { loginAction } from "@/lib/api/auth.actions";

// Using action wrapper
const result = await loginAction({ username, password });

// Or directly with clientApi
const result = await clientApi.post("/auth/login", { username, password });

if (result.ok) {
  // Success
  console.log(result.data);
} else {
  // Error
  setError(result.message); // Already formatted for display
}
```

## Benefits

1. **No Duplication**: Single source of truth for HTTP logic
2. **Consistent Error Handling**: All endpoints use same error normalization
3. **Type Safety**: Full TypeScript support with generic types
4. **Timeout Management**: Centralized timeout configuration
5. **Easy to Extend**: Add new methods to `serverApi` or `clientApi` without duplication
6. **Clear Separation**: Server-side and client-side concerns clearly separated
7. **Environment-Aware**: Backend URL resolution handles both server and client contexts

## Future Enhancements

- Add request/response interceptors for logging
- Add retry logic for transient errors
- Add request caching/deduplication
- Add analytics/tracing integration
- Add authentication token injection in serverApi
