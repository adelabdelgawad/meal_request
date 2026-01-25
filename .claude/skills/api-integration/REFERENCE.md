# API Integration Reference

Quick reference for Next.js to FastAPI integration.

## File Locations

| Component | Path |
|-----------|------|
| API Routes | `src/my-app/app/api/` |
| Server API Client | `src/my-app/lib/http/axios-server.ts` |
| Client API Client | `src/my-app/lib/http/axios-client.ts` |
| Server Actions | `src/my-app/lib/actions/*.actions.ts` |
| Client API Functions | `src/my-app/lib/api/*.ts` |

## Data Flow

```
Server Component Page
    ↓
Server Action (serverApi)
    ↓
Backend API
    ↓
Return to Page as initialData
    ↓
Pass to Client Component
    ↓
SWR with fallbackData
    ↓
User Interaction
    ↓
Client API Function (clientApi)
    ↓
Next.js API Route
    ↓
Backend API
```

## API Result Type

```typescript
interface ApiResult<T> {
  ok: boolean;
  data: T;
  error?: string;
  status: number;
}
```

## Server API Usage

```typescript
// GET with params
const result = await serverApi.get<UserListResponse>("/users", {
  params: { skip: 0, limit: 10 },
  useVersioning: true,
});

// POST
const result = await serverApi.post<User>("/users", userData);

// PUT
const result = await serverApi.put<User>(`/users/${id}`, updateData);

// DELETE
const result = await serverApi.delete(`/users/${id}`);
```

## Client API Usage

```typescript
// GET (to Next.js API route)
const result = await clientApi.get<UserListResponse>("/api/users?skip=0&limit=10");

// POST
const result = await clientApi.post<User>("/api/users", userData);

// PUT
const result = await clientApi.put<User>(`/api/users/${id}`, updateData);

// DELETE
const result = await clientApi.delete(`/api/users/${id}`);
```

## Cookie Handling

### Server-Side (Next.js API Routes)

```typescript
import { cookies } from "next/headers";

export async function GET() {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get("access_token")?.value;

  if (!accessToken) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // Use token in Authorization header
  headers: {
    Authorization: `Bearer ${accessToken}`,
  }
}
```

### Client-Side

```typescript
// credentials: "include" sends cookies automatically
const response = await fetch(url, {
  credentials: "include",
});
```

## SWR Configuration

```typescript
const { data, mutate } = useSWR(url, fetcher, {
  fallbackData: initialData,      // SSR data
  keepPreviousData: true,         // Smooth transitions
  revalidateOnMount: false,       // Don't refetch if we have data
  revalidateIfStale: true,        // Refetch if cache is old
  revalidateOnFocus: false,       // Don't refetch on tab focus
  revalidateOnReconnect: false,   // Don't refetch on reconnect
});
```

## Error Handling

```typescript
// In API function
const result = await clientApi.post<User>("/api/users", data);

if (!result.ok) {
  throw new Error(result.error || "Failed to create user");
}

return result.data;

// In component
try {
  const user = await createUser(data);
  toast.success("User created");
} catch (error) {
  toast.error(error.message);
}
```

## API Route Patterns

### GET with Query Params

```typescript
export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const url = new URL("/api/v1/endpoint", BACKEND_URL);
  searchParams.forEach((value, key) => {
    url.searchParams.append(key, value);
  });
  // ...
}
```

### POST with Body

```typescript
export async function POST(request: NextRequest) {
  const body = await request.json();
  // Forward body to backend
}
```

### Dynamic Route

```typescript
// app/api/users/[id]/route.ts
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const { id } = params;
  // Use id in backend call
}
```

## HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | OK | Return data |
| 201 | Created | Return new resource |
| 204 | No Content | Return empty |
| 400 | Bad Request | Show validation error |
| 401 | Unauthorized | Redirect to login |
| 403 | Forbidden | Show permission error |
| 404 | Not Found | Show not found message |
| 500 | Server Error | Show generic error |

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| 401 on all requests | Cookie not forwarded | Check cookie forwarding |
| CORS error | Missing credentials | Add `credentials: "include"` |
| Empty response | Wrong Content-Type | Set `Content-Type: application/json` |
| Type error | Untyped response | Add generic type to API call |
