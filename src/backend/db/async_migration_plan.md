# Async Database Migration Plan

## Overview
This document outlines the plan to migrate the remaining synchronous CRUD operations to asynchronous SQLAlchemy patterns to achieve consistency across the codebase.

## Current State Analysis

### ✅ **ASYNC CRUDs (AsyncSession, `await` operations)**
The following CRUD modules are already using async patterns correctly:
- `db/cruds/employee_crud.py` - ✅ Async (AsyncSession, await session.execute())
- `db/cruds/meal_request_crud.py` - ✅ Async (AsyncSession, await session.execute())  
- `db/cruds/meal_request_line_crud.py` - ✅ Async (AsyncSession, await session.execute())
- `db/cruds/account_crud.py` - ✅ Async (AsyncSession, await session.execute())

### ❌ **SYNC CRUDs (Session, sync operations)**
The following CRUD modules are using synchronous patterns and need migration:
- `db/cruds/tokens_crud.py` - ❌ Sync (Session, db.execute())
- `db/cruds/allowed_origins_crud.py` - ❌ Sync (Session, db.execute())

## Migration Strategy

### Phase 1: Core Security CRUD Migration (High Priority)
**Affected Files:**
- `db/cruds/tokens_crud.py`
- `db/cruds/allowed_origins_crud.py`

**Risk Level:** LOW - These are small, contained modules with clear async/await patterns already established in other CRUDs.

### Phase 2: Consistency Review (Medium Priority)
**Affected Files:** 
- All other CRUD modules to ensure consistent async patterns

## Detailed Migration Steps

### Step 1: Update Import Statements
```python
# FROM:
from sqlalchemy.orm import Session

# TO:
from sqlalchemy.ext.asyncio import AsyncSession
```

### Step 2: Convert Function Signatures
```python
# FROM:
def create_revoked_token(db: Session, ...) -> RevokedToken:

# TO:
async def create_revoked_token(db: AsyncSession, ...) -> RevokedToken:
```

### Step 3: Update Database Operations
```python
# FROM:
db.add(db_obj)
db.commit()
db.refresh(db_obj)

# TO:
db.add(db_obj)
await db.commit()
await db.refresh(db_obj)
```

### Step 4: Update Query Execution
```python
# FROM:
stmt = select(RevokedToken).where(RevokedToken.jti == jti)
return db.execute(stmt).scalars().first()

# TO:
stmt = select(RevokedToken).where(RevokedToken.jti == jti)
result = await db.execute(stmt)
return result.scalars().first()
```

### Step 5: Update Error Handling
```python
# FROM:
except SQLAlchemyError as e:
    db.rollback()

# TO:
except SQLAlchemyError as e:
    await db.rollback()
```

## Performance Risk Evaluation

### ✅ **Low Risk Factors:**
1. **Pattern Consistency**: Other CRUDs already demonstrate correct async patterns
2. **Module Size**: Small, contained modules (< 100 lines each)
3. **Dependency Chain**: Limited dependencies, not used in complex workflows
4. **Test Coverage**: Existing test structure can be adapted

### ⚠️ **Potential Risk Factors:**
1. **Mixed Usage**: Current sync modules might be called from async contexts
2. **Transaction Management**: Ensure proper async transaction handling
3. **Connection Pool**: Verify async connection pool configuration

## Testing Strategy

### 1. Unit Tests
- Convert existing sync tests to async patterns using `pytest-asyncio`
- Add proper async session mocking
- Test error handling scenarios

### 2. Integration Tests
- Test CRUD operations with real database
- Verify transaction rollback scenarios
- Test concurrent operations

### 3. Performance Tests
- Compare sync vs async performance
- Verify connection pool efficiency
- Monitor memory usage

## Rollout Plan

### Commit 1: Migrate `tokens_crud.py`
**Changes:**
- Convert all functions to async
- Update imports and type hints
- Add comprehensive async tests
- Update any direct callers

### Commit 2: Migrate `allowed_origins_crud.py`
**Changes:**
- Convert all functions to async
- Update imports and type hints
- Add comprehensive async tests
- Update any direct callers

### Commit 3: Integration Testing
**Changes:**
- Run full test suite with migrated modules
- Performance benchmarking
- Documentation updates

## Backward Compatibility

### ⚠️ **Breaking Changes:**
- All function signatures will change (sync → async)
- Callers must use `await` for all CRUD operations
- Error handling patterns must be async-aware

### 🔄 **Migration Path for Callers:**
```python
# FROM:
result = TokenCRUD.create_revoked_token(db_session, ...)

# TO:
result = await TokenCRUD.create_revoked_token(db_session, ...)
```

## Verification Checklist

### Before Migration:
- [ ] Identify all callers of sync CRUD functions
- [ ] Verify async database engine configuration
- [ ] Ensure proper async test infrastructure

### During Migration:
- [ ] Convert one module at a time
- [ ] Run tests after each conversion
- [ ] Update function documentation
- [ ] Verify type hints

### After Migration:
- [ ] Run full test suite
- [ ] Performance testing
- [ ] Update API documentation
- [ ] Monitor for runtime issues

## Success Criteria

### Technical Success:
- ✅ All CRUD operations use async/await patterns
- ✅ No synchronous database operations remain
- ✅ Full test coverage maintained
- ✅ Performance maintained or improved

### Operational Success:
- ✅ No runtime errors in production
- ✅ Proper connection pool management
- ✅ Consistent error handling across all CRUDs
- ✅ Documentation updated

## Timeline

**Estimated Duration:** 2-3 days
- Day 1: Migrate `tokens_crud.py` + testing
- Day 2: Migrate `allowed_origins_crud.py` + testing  
- Day 3: Integration testing + documentation

## Risk Mitigation

### If Issues Arise:
1. **Rollback Plan**: Keep backup branches with sync implementations
2. **Gradual Migration**: Migrate one function at a time
3. **Testing**: Extensive testing at each step
4. **Monitoring**: Close monitoring during rollout

## Conclusion

The async migration is **LOW RISK** due to:
- Small scope (2 modules, < 200 lines total)
- Established patterns already working in other CRUDs
- Clear async/await patterns to follow
- Good test coverage foundation

The migration will improve code consistency and set the foundation for better scalability and performance in database operations.