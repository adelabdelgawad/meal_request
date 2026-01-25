# Celery Async Pattern Plugin

Enforces the mandatory async event loop handling pattern for Celery tasks to prevent production crashes.

## Why This Matters

Celery workers run with gevent (`-P gevent`) which patches asyncio and creates an event loop. Using `asyncio.run()` directly causes:

- `RuntimeError: Task got Future attached to a different loop`
- `Event loop is closed` errors
- Database connection cleanup failures
- **Production crashes**

## What It Checks

1. **Direct asyncio.run()** - Flags usage outside of `_run_async()` helper
2. **Missing _run_async helper** - Flags async tasks without the helper
3. **Missing engine disposal** - Flags missing `finally` blocks for cleanup
4. **Return inside try** - Warns about returns before finally block

## Correct Pattern

```python
def _run_async(coro):
    """Event loop detection helper."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        # Running in gevent - use thread executor
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # No running loop - create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            pass

@shared_task(bind=True)
def my_task(self, execution_id=None):
    async def _execute():
        from db.maria_database import DatabaseSessionLocal, database_engine

        result = None
        try:
            async with DatabaseSessionLocal() as session:
                # Your async logic here
                result = {"status": "success"}
        finally:
            await database_engine.dispose()  # CRITICAL!

        return result  # Return AFTER finally

    return _run_async(_execute())
```

## Incorrect Patterns

```python
# WRONG - Direct asyncio.run()
@shared_task
def bad_task():
    asyncio.run(async_function())  # Will crash with gevent!

# WRONG - Missing engine disposal
@shared_task
def bad_task():
    async def _execute():
        async with DatabaseSessionLocal() as session:
            return {"status": "success"}
        # Engine never disposed - connection leak!
    return _run_async(_execute())

# WRONG - Return inside try
async def _execute():
    try:
        result = await do_work()
        return result  # Prevents finally from running properly
    finally:
        await engine.dispose()
```

## Hook Behavior

- **Type:** PostToolUse (advisory)
- **Trigger:** Write or Edit to `tasks/*.py` files
- **Excludes:** `__init__.py` and files without `@shared_task`
- **Action:** Prints warning message, does not block

## Reference Implementation

See `src/backend/tasks/hris.py` for the reference implementation of the correct pattern.
