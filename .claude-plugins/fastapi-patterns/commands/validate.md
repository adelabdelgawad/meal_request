---
description: Validate the entire backend codebase against established patterns
---

# Validate Backend Patterns

Run comprehensive validation of the FastAPI backend to check for pattern violations.

## Instructions

Run the validation script on the backend codebase:

```bash
python3 .claude-plugins/fastapi-patterns/scripts/validate_all.py --path src/backend --verbose
```

After running, analyze the output and:

1. **For ERRORS**: These MUST be fixed. They represent violations of critical patterns that will cause issues.

2. **For WARNINGS**: These SHOULD be fixed when possible. They indicate potential issues or non-standard patterns.

3. **For INFO**: These are suggestions for improvement but not critical.

## What Gets Validated

- **Schemas**: Must inherit from CamelModel, not BaseModel directly
- **Routers**: Should use proper dependency injection for sessions
- **Services**: Should not store sessions, should use domain exceptions
- **Repositories**: Should use async methods and flush() instead of commit()
- **Models**: Should use Mapped type hints with mapped_column()

## Example Output

```
============================================================
FASTAPI BACKEND VALIDATION REPORT
============================================================

Files checked: 45
Errors: 2
Warnings: 5
Info: 3

------------------------------------------------------------
FINDINGS
------------------------------------------------------------

ERRORS (2):
  [X] [SCHEMA_CAMEL_MODEL] Class 'UserCreate' should inherit from CamelModel
      File: src/backend/api/schemas/users.py:15
  [X] [SERVICE_NO_SESSION_STORAGE] Services should not store session
      File: src/backend/api/services/user_service.py:23

WARNINGS (5):
  [!] [REPOSITORY_NO_COMMIT] Repository should use flush(), not commit()
      File: src/backend/api/repositories/user_repo.py:45
```

Report the findings to the user with specific file locations and suggested fixes.
