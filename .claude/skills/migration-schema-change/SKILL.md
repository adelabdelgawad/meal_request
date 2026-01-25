---
name: migration-schema-change
description: |
  Assist with Alembic migrations while identifying high-risk changes and their downstream impacts.
  Use when creating migrations, modifying database schemas, adding/removing columns, changing
  enum types, or analyzing migration impact on HRIS sync, foreign keys, and external systems.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# Migration & Schema Change

## Overview

This skill helps create safe database migrations with proper impact analysis. The key challenges include:

- **Driver differences** - pymysql (sync) for Alembic vs aiomysql (async) for app
- **HRIS dependencies** - Fields used by sync logic require careful handling
- **Enum changes** - Require data migration scripts
- **Foreign key cascades** - Can cause unintended data loss
- **Rollback capability** - Every migration needs a downgrade path

> **CRITICAL**: Always analyze impact on HRIS sync before modifying user-related fields.

## When to Use This Skill

Activate when request involves:

- Creating new Alembic migrations
- Adding or removing database columns
- Modifying enum values
- Changing foreign key relationships
- Analyzing migration impact
- Rolling back migrations
- Creating data migration scripts
- Modifying fields used by HRIS sync

## Quick Reference

### File Locations

| Component | Path |
|-----------|------|
| Alembic Config | `src/backend/alembic.ini` |
| Migration Scripts | `src/backend/alembic/versions/` |
| Env Config | `src/backend/alembic/env.py` |
| Models | `src/backend/db/models.py` |
| HRIS Sync | `src/backend/utils/replicate_hris.py` |

### Common Commands

```bash
cd src/backend

# Create migration
alembic revision --autogenerate -m "Description of change"

# Run migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

## Core Pattern: Safe Migration

### Basic Migration Template

```python
"""Add feature_flag column to user table.

Revision ID: abc123def456
Revises: previous_revision
Create Date: 2025-01-07 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = 'abc123def456'
down_revision: Union[str, None] = 'previous_revision'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add feature_flag column with default value."""
    op.add_column(
        'user',
        sa.Column(
            'feature_flag',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('FALSE'),
        )
    )


def downgrade() -> None:
    """Remove feature_flag column."""
    op.drop_column('user', 'feature_flag')
```

## High-Risk Field Identification

### Fields Used by HRIS Sync

Before modifying these fields, check `utils/replicate_hris.py`:

```python
# User fields managed by HRIS sync
HRIS_MANAGED_FIELDS = [
    'user_source',       # 'hris' or 'manual'
    'status_override',   # Override HRIS status changes
    'override_reason',
    'override_set_by_id',
    'override_set_at',
    'employee_id',       # Link to Employee table
    'is_domain_user',    # LDAP vs local auth
]

# Security user fields from HRIS
SECURITY_USER_FIELDS = [
    'is_deleted',
    'is_locked',
    'employee_id',
]
```

### Impact Analysis Checklist

Before creating a migration:

- [ ] Check if field is used in `replicate_hris.py`
- [ ] Check for foreign key references
- [ ] Check for index dependencies
- [ ] Check if field is used in scheduler tasks
- [ ] Check frontend type definitions that need updating

## Enum Change Pattern

### Adding Enum Value

```python
def upgrade() -> None:
    """Add 'contractor' to user_source enum."""
    # MySQL requires recreating the column for enum changes
    op.execute(
        "ALTER TABLE user MODIFY COLUMN user_source "
        "ENUM('hris', 'manual', 'contractor') NOT NULL DEFAULT 'hris'"
    )


def downgrade() -> None:
    """Remove 'contractor' from user_source enum."""
    # First, update any rows using the value being removed
    op.execute(
        "UPDATE user SET user_source = 'manual' WHERE user_source = 'contractor'"
    )
    # Then modify the column
    op.execute(
        "ALTER TABLE user MODIFY COLUMN user_source "
        "ENUM('hris', 'manual') NOT NULL DEFAULT 'hris'"
    )
```

### Removing Enum Value

```python
def upgrade() -> None:
    """Remove 'ldap' from user_source enum."""
    # CRITICAL: Migrate data FIRST
    op.execute("""
        UPDATE user
        SET user_source = CASE
            WHEN is_domain_user = TRUE AND employee_id IS NOT NULL THEN 'hris'
            ELSE 'manual'
        END
        WHERE user_source = 'ldap'
    """)

    # Then remove the enum value
    op.execute(
        "ALTER TABLE user MODIFY COLUMN user_source "
        "ENUM('hris', 'manual') NOT NULL DEFAULT 'hris'"
    )


def downgrade() -> None:
    """Re-add 'ldap' to user_source enum."""
    op.execute(
        "ALTER TABLE user MODIFY COLUMN user_source "
        "ENUM('hris', 'manual', 'ldap') NOT NULL DEFAULT 'hris'"
    )
    # Note: Cannot restore original 'ldap' values after upgrade
```

## Foreign Key Pattern

### Adding Foreign Key with Data

```python
def upgrade() -> None:
    """Add department_id foreign key to user table."""
    # 1. Add column as nullable first
    op.add_column(
        'user',
        sa.Column('department_id', sa.Integer(), nullable=True)
    )

    # 2. Populate data (if needed)
    # This example assigns a default department
    op.execute("""
        UPDATE user
        SET department_id = (SELECT id FROM department WHERE code = 'DEFAULT')
        WHERE department_id IS NULL
    """)

    # 3. Add foreign key constraint
    op.create_foreign_key(
        'fk_user_department',
        'user', 'department',
        ['department_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Remove department_id foreign key from user table."""
    op.drop_constraint('fk_user_department', 'user', type_='foreignkey')
    op.drop_column('user', 'department_id')
```

### Safe Foreign Key Deletion

```python
def upgrade() -> None:
    """Remove category_id from product (with cascade check)."""
    # First verify no orphaned references
    op.execute("""
        -- This will fail if there are orphaned records
        SELECT COUNT(*) FROM product p
        LEFT JOIN category c ON p.category_id = c.id
        WHERE p.category_id IS NOT NULL AND c.id IS NULL
    """)

    op.drop_constraint('fk_product_category', 'product', type_='foreignkey')
    op.drop_column('product', 'category_id')


def downgrade() -> None:
    """Re-add category_id to product."""
    op.add_column(
        'product',
        sa.Column('category_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_product_category',
        'product', 'category',
        ['category_id'], ['id']
    )
```

## NOT NULL Column Pattern

### Adding NOT NULL with Default

```python
def upgrade() -> None:
    """Add required field with server default."""
    # Add with server_default so existing rows get the value
    op.add_column(
        'user',
        sa.Column(
            'notification_enabled',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('TRUE'),
        )
    )


def downgrade() -> None:
    op.drop_column('user', 'notification_enabled')
```

### Converting Nullable to NOT NULL

```python
def upgrade() -> None:
    """Make email column required."""
    # 1. Update NULL values first
    op.execute("""
        UPDATE user
        SET email = CONCAT(username, '@company.com')
        WHERE email IS NULL
    """)

    # 2. Alter column to NOT NULL
    op.alter_column(
        'user',
        'email',
        existing_type=sa.String(255),
        nullable=False
    )


def downgrade() -> None:
    """Make email column nullable again."""
    op.alter_column(
        'user',
        'email',
        existing_type=sa.String(255),
        nullable=True
    )
```

## Allowed Operations

**DO:**
- Include rollback logic in every migration
- Migrate data before modifying constraints
- Check HRIS sync dependencies
- Add indexes for frequently queried columns
- Use server_default for new NOT NULL columns
- Test migrations on a copy of production data

**DON'T:**
- Drop columns without checking dependencies
- Remove enum values without data migration
- Add NOT NULL without default value
- Skip downgrade function
- Modify HRIS-managed fields without coordination
- Run migrations without backup

## Validation Checklist

Before running a migration:

- [ ] Downgrade function implemented
- [ ] Data migration included if needed
- [ ] HRIS sync impact analyzed
- [ ] Foreign key cascades checked
- [ ] Indexes added for new columns if needed
- [ ] NOT NULL columns have server_default
- [ ] TypeScript types updated
- [ ] Tests updated

## Additional Resources

- [PATTERNS.md](PATTERNS.md) - Detailed migration patterns
- [REFERENCE.md](REFERENCE.md) - Command reference

## Trigger Phrases

- "migration", "alembic", "schema change"
- "add column", "drop column", "alter column"
- "enum", "foreign key", "constraint"
- "rollback", "downgrade", "upgrade"
- "NOT NULL", "nullable", "default"
- "HRIS sync", "user_source", "status_override"
