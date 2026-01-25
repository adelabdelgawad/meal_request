# Migration Reference

Quick reference for Alembic migrations.

## Commands

| Command | Description |
|---------|-------------|
| `alembic revision --autogenerate -m "message"` | Create migration from model changes |
| `alembic revision -m "message"` | Create empty migration |
| `alembic upgrade head` | Run all pending migrations |
| `alembic upgrade +1` | Run next migration |
| `alembic downgrade -1` | Rollback one migration |
| `alembic downgrade base` | Rollback all migrations |
| `alembic current` | Show current revision |
| `alembic history` | Show migration history |
| `alembic show <revision>` | Show migration details |
| `alembic heads` | Show latest revision(s) |

## File Locations

| File | Purpose |
|------|---------|
| `src/backend/alembic.ini` | Alembic configuration |
| `src/backend/alembic/env.py` | Migration environment setup |
| `src/backend/alembic/versions/` | Migration scripts |
| `src/backend/db/models.py` | SQLAlchemy models |

## Migration Structure

```python
"""Migration description.

Revision ID: abc123def456
Revises: previous_revision
Create Date: 2025-01-07 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'abc123def456'
down_revision: Union[str, None] = 'previous_revision'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration."""
    pass


def downgrade() -> None:
    """Reverse migration."""
    pass
```

## Common Operations

### Add Column

```python
op.add_column('table', sa.Column('column', sa.String(100), nullable=True))
```

### Drop Column

```python
op.drop_column('table', 'column')
```

### Alter Column

```python
op.alter_column('table', 'column',
    existing_type=sa.String(100),
    type_=sa.String(200),
    nullable=False
)
```

### Rename Column

```python
op.alter_column('table', 'old_name',
    new_column_name='new_name',
    existing_type=sa.String(100)
)
```

### Create Table

```python
op.create_table('table',
    sa.Column('id', sa.Integer(), primary_key=True),
    sa.Column('name', sa.String(100), nullable=False),
)
```

### Drop Table

```python
op.drop_table('table')
```

### Create Index

```python
op.create_index('ix_table_column', 'table', ['column'])
```

### Drop Index

```python
op.drop_index('ix_table_column', table_name='table')
```

### Create Foreign Key

```python
op.create_foreign_key('fk_name', 'source_table', 'target_table',
    ['source_column'], ['target_column'],
    ondelete='CASCADE'
)
```

### Drop Foreign Key

```python
op.drop_constraint('fk_name', 'table', type_='foreignkey')
```

### Create Unique Constraint

```python
op.create_unique_constraint('uq_name', 'table', ['column'])
```

### Drop Unique Constraint

```python
op.drop_constraint('uq_name', 'table', type_='unique')
```

### Execute Raw SQL

```python
op.execute("UPDATE table SET column = 'value'")
```

## Data Types

| SQLAlchemy | MySQL |
|------------|-------|
| `sa.Integer()` | `INT` |
| `sa.BigInteger()` | `BIGINT` |
| `sa.SmallInteger()` | `SMALLINT` |
| `sa.String(n)` | `VARCHAR(n)` |
| `sa.Text()` | `TEXT` |
| `sa.Boolean()` | `TINYINT(1)` |
| `sa.DateTime()` | `DATETIME` |
| `sa.DateTime(timezone=True)` | `DATETIME` |
| `sa.Date()` | `DATE` |
| `sa.Time()` | `TIME` |
| `sa.Float()` | `FLOAT` |
| `sa.Numeric(p, s)` | `DECIMAL(p, s)` |
| `sa.JSON()` | `JSON` |
| `sa.Enum('a', 'b')` | `ENUM('a', 'b')` |

## Server Defaults

```python
# Boolean false
server_default=sa.text('FALSE')

# Boolean true
server_default=sa.text('TRUE')

# Current timestamp
server_default=sa.text('CURRENT_TIMESTAMP')

# String value
server_default='default_value'

# Integer value
server_default='0'
```

## Foreign Key Options

| Option | Description |
|--------|-------------|
| `ondelete='CASCADE'` | Delete children when parent deleted |
| `ondelete='SET NULL'` | Set to NULL when parent deleted |
| `ondelete='RESTRICT'` | Prevent parent deletion if children exist |
| `onupdate='CASCADE'` | Update children when parent key changes |

## HRIS-Managed Fields

These fields in `user` table are managed by HRIS sync:

| Field | Description |
|-------|-------------|
| `user_source` | 'hris' or 'manual' |
| `status_override` | Override HRIS status changes |
| `override_reason` | Justification for override |
| `override_set_by_id` | Admin who set override |
| `override_set_at` | When override was set |
| `employee_id` | Link to Employee table |
| `is_domain_user` | LDAP vs local auth |

## Pre-Migration Checklist

- [ ] Backup database
- [ ] Review model changes
- [ ] Check HRIS sync impact
- [ ] Test on staging
- [ ] Plan rollback

## Post-Migration Checklist

- [ ] Verify `alembic current`
- [ ] Check data integrity
- [ ] Update TypeScript types
- [ ] Update documentation
- [ ] Test affected features
