# Diagnose Empty Requests Page

The page at http://localhost:3000/requests is loading empty. Here's how to diagnose:

## 1. Check if You're Logged In

The `/requests/all` endpoint requires authentication. If you're not logged in:
- The API returns `401 Not authenticated`
- The frontend catches this error and returns empty data
- Result: Empty page (no error message shown)

**Solution**: Go to http://localhost:3000/login and log in first

## 2. Check Next.js Server Logs

The server-side API calls log errors. Check your Next.js terminal for:

```
[axios-server] ❌ Error Response [GET /api/v1/requests/all]
{
  status: 401,
  statusText: 'Unauthorized',
  data: { detail: 'Not authenticated' }
}
```

If you see this, you need to log in.

## 3. Check Browser Console

Open browser DevTools (F12) and check the Console tab for:
- `Failed to fetch meal requests: ...`
- Any other error messages

## 4. Check Network Tab

In DevTools Network tab:
1. Refresh http://localhost:3000/requests
2. Look for the initial page load request
3. Check if cookies are being sent (should include `access_token`)
4. Look for any 401/403 responses

## 5. Verify Authentication Cookies

In DevTools Application tab → Cookies → http://localhost:3000:
- Check if `access_token` cookie exists
- Check if `refresh_token` cookie exists
- If missing, you need to log in

## 6. Test Backend API Directly

With authentication token:
```bash
# Get your access token from browser cookies (Application tab)
TOKEN="your_token_here"

# Test the endpoint
curl -H "Authorization: Bearer $TOKEN" \
  'http://localhost:8000/api/v1/requests/all?page=1&page_size=10'
```

## Quick Fix

**Most likely cause**: You're not logged in

**Solution**:
1. Go to http://localhost:3000/login
2. Log in with your credentials
3. Navigate back to http://localhost:3000/requests
4. The page should now show data

## If Still Empty After Login

If you're logged in but still seeing empty:

1. **Check user roles**: You might not have permission to view requests
   - Required roles: Ordertaker, Auditor, or Admin

2. **Check department filtering**:
   - The backend might be filtering requests by your department assignments
   - If you have no department assignments but also no data, check backend logs

3. **Check database for requests with lines**:
   ```sql
   SELECT COUNT(*) FROM meal_request mr
   JOIN meal_request_line mrl ON mr.id = mrl.meal_request_id
   WHERE mr.is_deleted = FALSE
   AND mrl.is_deleted = FALSE
   AND mr.status_id != 4;  -- Exclude "On Progress" status
   ```

## Enable Debug Logging

To see more detailed logs in Next.js server:

1. Check `src/my-app/lib/actions/requests.actions.ts`
2. Look for console.error messages in your Next.js terminal
3. Errors are logged when API calls fail

## Common Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| Empty page, no error | Not authenticated | Log in first |
| 403 Forbidden | Wrong role | Need Ordertaker/Auditor/Admin role |
| Empty with "0 results" | No data matches filters | Clear filters or add data |
| Page won't load at all | Frontend not running | Start Next.js: `npm run dev` |
| API errors in console | Backend not running | Start backend |

---

**Bottom line**: Most likely you just need to log in at http://localhost:3000/login
