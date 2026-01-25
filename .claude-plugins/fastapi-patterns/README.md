# FastAPI Patterns Plugin

A Claude Code plugin that enforces FastAPI + SQLAlchemy + Pydantic patterns for consistent backend development.

## Features

- **Pre-write validation**: Validates code before it's written to ensure pattern compliance
- **Post-write checks**: Provides suggestions after code is written
- **Slash commands**: Generate boilerplate code following patterns
- **Backend skill**: Teaches Claude all the established patterns

## Installation

### Local Development

```bash
# Test the plugin locally
claude --plugin-dir .claude-plugins/fastapi-patterns
```

### Project Installation

Add to your project's `.claude/settings.json`:

```json
{
  "plugins": [
    ".claude-plugins/fastapi-patterns"
  ]
}
```

## Slash Commands

| Command | Description |
|---------|-------------|
| `/fastapi-patterns:validate` | Validate entire backend against patterns |
| `/fastapi-patterns:scaffold-router` | Generate a new router with CRUD endpoints |
| `/fastapi-patterns:scaffold-schema` | Generate Pydantic schemas with CamelModel |
| `/fastapi-patterns:scaffold-service` | Generate a service layer class |
| `/fastapi-patterns:scaffold-repository` | Generate a repository class |
| `/fastapi-patterns:check-schema` | Check a schema file for CamelModel compliance |

## Validation Rules

### Schema Rules

| Rule | Severity | Description |
|------|----------|-------------|
| `SCHEMA_CAMEL_MODEL` | Error | Schemas must inherit from CamelModel |
| `SCHEMA_NO_ALIAS_GENERATOR` | Warning | Don't use manual alias_generator |
| `SCHEMA_NO_MANUAL_CAMEL_ALIAS` | Warning | Don't use Field(alias="camelCase") |

### Service Rules

| Rule | Severity | Description |
|------|----------|-------------|
| `SERVICE_NO_SESSION_STORAGE` | Error | Don't store session as instance variable |
| `SERVICE_NO_HTTP_EXCEPTION` | Warning | Use domain exceptions, not HTTPException |

### Repository Rules

| Rule | Severity | Description |
|------|----------|-------------|
| `REPOSITORY_NO_COMMIT` | Warning | Use flush(), not commit() |
| `REPOSITORY_ASYNC_METHODS` | Warning | Methods should be async |

### Model Rules

| Rule | Severity | Description |
|------|----------|-------------|
| `MODEL_USE_MAPPED` | Warning | Use Mapped type hints |
| `MODEL_UUID_CHAR36` | Info | Store UUIDs as CHAR(36) |

## Validation Script

Run manual validation:

```bash
# Validate entire backend
python .claude-plugins/fastapi-patterns/scripts/validate_all.py --path src/backend --verbose

# Output as JSON
python .claude-plugins/fastapi-patterns/scripts/validate_all.py --path src/backend --json
```

## Key Patterns

### CamelModel (MANDATORY)

All Pydantic schemas MUST inherit from `CamelModel`:

```python
# CORRECT
from api.schemas._base import CamelModel

class UserCreate(CamelModel):
    user_name: str  # Becomes "userName" in JSON
    is_active: bool # Becomes "isActive" in JSON

# WRONG - Don't do this!
from pydantic import BaseModel
class UserCreate(BaseModel):  # ❌
    pass
```

### Layered Architecture

```
Router (API) → Service (Business Logic) → Repository (Data Access) → Model (ORM)
```

- **Routers**: Handle HTTP, use Depends() for injection
- **Services**: Business logic, raise domain exceptions
- **Repositories**: Data access, use async methods
- **Models**: SQLAlchemy ORM definitions

### Session Management

```python
# CORRECT - Pass session to each method
class MyService:
    async def create(self, session: AsyncSession, data):
        ...

# WRONG - Don't store session
class MyService:
    def __init__(self, session):
        self.session = session  # ❌
```

## Directory Structure

```
.claude-plugins/fastapi-patterns/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest
├── commands/                     # Slash commands
│   ├── validate.md
│   ├── scaffold-router.md
│   ├── scaffold-schema.md
│   ├── scaffold-service.md
│   ├── scaffold-repository.md
│   └── check-schema.md
├── skills/
│   └── backend-patterns/         # Backend development skill
│       ├── SKILL.md
│       ├── PATTERNS.md
│       └── REFERENCE.md
├── scripts/                      # Validation scripts
│   ├── pre_write_validator.py
│   ├── post_write_checker.py
│   └── validate_all.py
├── hooks/
│   └── hooks.json               # Pre/post write hooks
└── README.md
```

## Hooks

The plugin uses hooks to validate code during development:

- **PreToolUse** (Write/Edit): Validates patterns before writing
- **PostToolUse** (Write/Edit): Provides suggestions after writing

Hooks can be disabled by removing the `hooks` configuration from `plugin.json`.

## Contributing

When adding new patterns:

1. Add validation logic to `scripts/pre_write_validator.py`
2. Add check to `scripts/validate_all.py`
3. Document in `skills/backend-patterns/PATTERNS.md`
4. Update this README

## License

Internal use only.
