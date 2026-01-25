# Migration Patterns

Detailed patterns for common migration scenarios.

## Index Management

### Adding Index

```python
def upgrade() -> None:
    """Add index for frequently filtered columns."""
    op.create_index(
        'ix_user_is_active',
        'user',
        ['is_active'],
        unique=False
    )

    # Composite index
    op.create_index(
        'ix_user_source_override',
        'user',
        ['user_source', 'status_override'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_user_source_override', table_name='user')
    op.drop_index('ix_user_is_active', table_name='user')
```

### Adding Unique Constraint

```python
def upgrade() -> None:
    """Add unique constraint on username."""
    # First check for duplicates
    op.execute("""
        SELECT username, COUNT(*) as cnt
        FROM user
        GROUP BY username
        HAVING cnt > 1
    """)
    # If query returns results, migration will need data cleanup first

    op.create_unique_constraint(
        'uq_user_username',
        'user',
        ['username']
    )


def downgrade() -> None:
    op.drop_constraint('uq_user_username', 'user', type_='unique')
```

---

## Table Operations

### Creating Table

```python
def upgrade() -> None:
    """Create audit_log table."""
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.String(36), nullable=False),
        sa.Column('old_value', sa.JSON(), nullable=True),
        sa.Column('new_value', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
    )

    op.create_index('ix_audit_log_entity', 'audit_log', ['entity_type', 'entity_id'])
    op.create_index('ix_audit_log_user', 'audit_log', ['user_id'])
    op.create_index('ix_audit_log_created', 'audit_log', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_audit_log_created', table_name='audit_log')
    op.drop_index('ix_audit_log_user', table_name='audit_log')
    op.drop_index('ix_audit_log_entity', table_name='audit_log')
    op.drop_table('audit_log')
```

### Renaming Table

```python
def upgrade() -> None:
    """Rename account to user."""
    op.rename_table('account', 'user')

    # Update foreign key references
    op.drop_constraint('fk_role_permission_account', 'role_permission', type_='foreignkey')
    op.alter_column('role_permission', 'account_id', new_column_name='user_id')
    op.create_foreign_key(
        'fk_role_permission_user',
        'role_permission', 'user',
        ['user_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_role_permission_user', 'role_permission', type_='foreignkey')
    op.alter_column('role_permission', 'user_id', new_column_name='account_id')
    op.create_foreign_key(
        'fk_role_permission_account',
        'role_permission', 'account',
        ['account_id'], ['id']
    )
    op.rename_table('user', 'account')
```

---

## Column Operations

### Renaming Column

```python
def upgrade() -> None:
    """Rename full_name_en to full_name."""
    # MySQL requires specifying the column type
    op.alter_column(
        'user',
        'full_name_en',
        new_column_name='full_name',
        existing_type=sa.String(255),
    )


def downgrade() -> None:
    op.alter_column(
        'user',
        'full_name',
        new_column_name='full_name_en',
        existing_type=sa.String(255),
    )
```

### Changing Column Type

```python
def upgrade() -> None:
    """Change description from VARCHAR to TEXT."""
    op.alter_column(
        'role',
        'description_en',
        existing_type=sa.String(255),
        type_=sa.Text(),
    )


def downgrade() -> None:
    # Warning: This may truncate data!
    op.execute("""
        UPDATE role
        SET description_en = LEFT(description_en, 255)
        WHERE LENGTH(description_en) > 255
    """)

    op.alter_column(
        'role',
        'description_en',
        existing_type=sa.Text(),
        type_=sa.String(255),
    )
```

---

## Data Migration Patterns

### Backfill Data

```python
def upgrade() -> None:
    """Add computed column with backfill."""
    # Add column
    op.add_column(
        'meal_request',
        sa.Column('total_quantity', sa.Integer(), nullable=True)
    )

    # Backfill from related table
    op.execute("""
        UPDATE meal_request mr
        SET total_quantity = (
            SELECT COALESCE(SUM(quantity), 0)
            FROM meal_request_line mrl
            WHERE mrl.meal_request_id = mr.id
        )
    """)

    # Now make NOT NULL
    op.alter_column(
        'meal_request',
        'total_quantity',
        existing_type=sa.Integer(),
        nullable=False,
        server_default='0'
    )


def downgrade() -> None:
    op.drop_column('meal_request', 'total_quantity')
```

### Batch Data Migration

```python
def upgrade() -> None:
    """Migrate large dataset in batches."""
    connection = op.get_bind()

    # Add new column
    op.add_column(
        'large_table',
        sa.Column('new_status', sa.String(20), nullable=True)
    )

    # Migrate in batches
    batch_size = 10000
    offset = 0

    while True:
        result = connection.execute(sa.text(f"""
            UPDATE large_table
            SET new_status = CASE
                WHEN old_status = 1 THEN 'active'
                WHEN old_status = 2 THEN 'inactive'
                ELSE 'unknown'
            END
            WHERE new_status IS NULL
            LIMIT {batch_size}
        """))

        if result.rowcount == 0:
            break

        print(f"Migrated {offset + result.rowcount} rows...")
        offset += batch_size

    # Make column NOT NULL
    op.alter_column(
        'large_table',
        'new_status',
        existing_type=sa.String(20),
        nullable=False
    )

    # Drop old column
    op.drop_column('large_table', 'old_status')


def downgrade() -> None:
    # Reverse the process...
    pass
```

---

## HRIS Sync Safe Patterns

### Modifying User Source Field

```python
def upgrade() -> None:
    """Add new user source type."""
    # Check replicate_hris.py for impact
    # This change affects Phase 6 user sync

    op.execute(
        "ALTER TABLE user MODIFY COLUMN user_source "
        "ENUM('hris', 'manual', 'service_account') NOT NULL DEFAULT 'hris'"
    )

    # Log for audit trail
    op.execute("""
        INSERT INTO log_configuration (
            action, entity_type, details, created_at
        ) VALUES (
            'SCHEMA_CHANGE',
            'user',
            '{"field": "user_source", "change": "added service_account"}',
            NOW()
        )
    """)


def downgrade() -> None:
    # Migrate service_account to manual before removing
    op.execute("""
        UPDATE user
        SET user_source = 'manual'
        WHERE user_source = 'service_account'
    """)

    op.execute(
        "ALTER TABLE user MODIFY COLUMN user_source "
        "ENUM('hris', 'manual') NOT NULL DEFAULT 'hris'"
    )
```

### Adding Status Override Fields

```python
def upgrade() -> None:
    """Add status override fields for HRIS sync conflict resolution."""
    # status_override: If true, HRIS sync won't modify is_active
    op.add_column(
        'user',
        sa.Column(
            'status_override',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('FALSE'),
        )
    )

    # override_reason: Required justification
    op.add_column(
        'user',
        sa.Column('override_reason', sa.Text(), nullable=True)
    )

    # override_set_by_id: Admin who enabled override
    op.add_column(
        'user',
        sa.Column('override_set_by_id', sa.String(36), nullable=True)
    )

    # override_set_at: When override was enabled
    op.add_column(
        'user',
        sa.Column('override_set_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Foreign key for override_set_by_id
    op.create_foreign_key(
        'fk_user_override_set_by',
        'user', 'user',
        ['override_set_by_id'], ['id'],
        ondelete='SET NULL'
    )

    # Index for sync performance
    op.create_index(
        'ix_user_source_override',
        'user',
        ['user_source', 'status_override']
    )


def downgrade() -> None:
    op.drop_index('ix_user_source_override', table_name='user')
    op.drop_constraint('fk_user_override_set_by', 'user', type_='foreignkey')
    op.drop_column('user', 'override_set_at')
    op.drop_column('user', 'override_set_by_id')
    op.drop_column('user', 'override_reason')
    op.drop_column('user', 'status_override')
```

---

## Scheduler-Related Migrations

### Adding Job Fields

```python
def upgrade() -> None:
    """Add priority and coalesce fields to scheduled_job."""
    op.add_column(
        'scheduled_job',
        sa.Column(
            'priority',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Higher priority runs first'
        )
    )

    op.add_column(
        'scheduled_job',
        sa.Column(
            'coalesce',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('TRUE'),
            comment='Combine missed runs into single execution'
        )
    )

    # Index for ordering by priority
    op.create_index(
        'ix_scheduled_job_priority',
        'scheduled_job',
        ['priority', 'id'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_scheduled_job_priority', table_name='scheduled_job')
    op.drop_column('scheduled_job', 'coalesce')
    op.drop_column('scheduled_job', 'priority')
```

---

## Testing Migrations

### Pre-Migration Checks

```python
def upgrade() -> None:
    """Migration with pre-flight checks."""
    connection = op.get_bind()

    # Check for data that would violate new constraint
    result = connection.execute(sa.text("""
        SELECT COUNT(*) as cnt FROM user WHERE email IS NULL
    """))
    null_count = result.scalar()

    if null_count > 0:
        raise Exception(
            f"Cannot add NOT NULL constraint: {null_count} rows have NULL email. "
            "Run data cleanup migration first."
        )

    # Safe to proceed
    op.alter_column(
        'user',
        'email',
        existing_type=sa.String(255),
        nullable=False
    )
```

### Post-Migration Verification

```bash
# After running migration
alembic current  # Verify version

# Check constraint was applied
mysql -e "DESCRIBE user;" | grep email

# Verify data integrity
mysql -e "SELECT COUNT(*) FROM user WHERE email IS NULL;"
```

---

## Common Mistakes to Avoid

### 1. Missing Downgrade

```python
# ❌ WRONG
def downgrade() -> None:
    pass  # No rollback capability!

# ✅ CORRECT
def downgrade() -> None:
    op.drop_column('user', 'new_column')
```

### 2. Adding NOT NULL Without Default

```python
# ❌ WRONG - Will fail on existing rows
op.add_column('user', sa.Column('required_field', sa.String(50), nullable=False))

# ✅ CORRECT
op.add_column('user', sa.Column('required_field', sa.String(50), nullable=False,
                                server_default='default_value'))
```

### 3. Removing Enum Value Without Data Migration

```python
# ❌ WRONG - Will fail if rows use the value
op.execute("ALTER TABLE user MODIFY COLUMN status ENUM('active', 'inactive')")

# ✅ CORRECT
op.execute("UPDATE user SET status = 'inactive' WHERE status = 'pending'")
op.execute("ALTER TABLE user MODIFY COLUMN status ENUM('active', 'inactive')")
```

### 4. Not Checking Foreign Keys

```python
# ❌ WRONG - May leave orphaned references
op.drop_table('category')

# ✅ CORRECT
# First check for references
op.execute("SELECT * FROM product WHERE category_id IS NOT NULL")
# Handle them, then drop
op.drop_table('category')
```
