#!/usr/bin/env python3
"""
Pre-write validator for FastAPI backend patterns.

This script validates code BEFORE it's written to ensure it follows
the established patterns. Receives tool input via stdin as JSON.

Exit codes:
  0 - Allow the write
  2 - Block the write (pattern violation)
"""

import json
import re
import sys
from pathlib import Path


def get_tool_input():
    """Read tool input from stdin."""
    try:
        data = json.load(sys.stdin)
        return data.get("tool_input", {})
    except (json.JSONDecodeError, KeyError):
        return {}


def is_backend_file(file_path: str) -> bool:
    """Check if file is in the backend directory."""
    return "src/backend" in file_path


def is_schema_file(file_path: str) -> bool:
    """Check if file is a Pydantic schema file."""
    return "schemas" in file_path and file_path.endswith(".py")


def is_router_file(file_path: str) -> bool:
    """Check if file is a router file."""
    return "api/v1" in file_path and file_path.endswith(".py")


def is_service_file(file_path: str) -> bool:
    """Check if file is a service file."""
    return "services" in file_path and file_path.endswith(".py")


def is_repository_file(file_path: str) -> bool:
    """Check if file is a repository file."""
    return "repositories" in file_path and file_path.endswith(".py")


def is_model_file(file_path: str) -> bool:
    """Check if file is a model file."""
    return "models.py" in file_path or "db/models" in file_path


def validate_schema_content(content: str, file_path: str) -> list:
    """Validate Pydantic schema patterns."""
    errors = []

    # Skip base file itself
    if "_base.py" in file_path:
        return errors

    # Check for class definitions
    class_pattern = r"class\s+(\w+)\s*\(([\w\s,\.]+)\)"
    classes = re.findall(class_pattern, content)

    for class_name, bases in classes:
        bases_clean = bases.replace(" ", "").split(",")

        # Schema classes should inherit from CamelModel
        if any(suffix in class_name for suffix in ["Create", "Update", "Response", "Base", "Request"]):
            if "CamelModel" not in bases_clean and "BaseModel" not in bases_clean:
                continue  # Might be inheriting from another schema

            if "BaseModel" in bases_clean and "CamelModel" not in bases_clean:
                errors.append({
                    "rule": "SCHEMA_CAMEL_MODEL",
                    "message": f"Class '{class_name}' inherits from BaseModel directly. Use CamelModel instead.",
                    "suggestion": f"Change 'class {class_name}(BaseModel)' to 'class {class_name}(CamelModel)'",
                    "severity": "error"
                })

    # Check for manual alias_generator (should use CamelModel)
    if "alias_generator" in content and "to_camel" in content:
        if "_base.py" not in file_path:
            errors.append({
                "rule": "SCHEMA_NO_MANUAL_ALIAS",
                "message": "Manual alias_generator detected. CamelModel handles this automatically.",
                "suggestion": "Remove alias_generator and inherit from CamelModel",
                "severity": "warning"
            })

    # Check for Field(alias=...) for camelCase conversion
    manual_alias_pattern = r'Field\s*\([^)]*alias\s*=\s*["\']([a-z]+[A-Z][a-zA-Z]*)["\']'
    manual_aliases = re.findall(manual_alias_pattern, content)
    if manual_aliases:
        errors.append({
            "rule": "SCHEMA_NO_MANUAL_CAMEL_ALIAS",
            "message": f"Manual camelCase aliases detected: {manual_aliases}. CamelModel handles this.",
            "suggestion": "Remove manual alias definitions and use snake_case field names",
            "severity": "warning"
        })

    return errors


def validate_router_content(content: str, file_path: str) -> list:
    """Validate FastAPI router patterns."""
    errors = []

    # Check for session dependency
    if "async def" in content and "@router" in content:
        if "Depends(get_session)" not in content and "Depends(get_maria_session)" not in content:
            # Check if it's a route that needs DB access
            if "session:" in content or "Session" in content:
                errors.append({
                    "rule": "ROUTER_SESSION_DEPENDENCY",
                    "message": "Router endpoints should use Depends(get_session) for database access",
                    "suggestion": "Add 'session: AsyncSession = Depends(get_session)' to endpoint parameters",
                    "severity": "warning"
                })

    # Check for proper response_model usage
    endpoint_pattern = r'@router\.(get|post|put|patch|delete)\s*\([^)]*\)\s*\n\s*async\s+def\s+(\w+)'
    endpoints = re.findall(endpoint_pattern, content)

    for method, func_name in endpoints:
        # Check if endpoint has response_model
        func_start = content.find(f"def {func_name}")
        if func_start != -1:
            decorator_region = content[max(0, func_start - 500):func_start]
            if "response_model" not in decorator_region and method != "delete":
                # This is a soft warning - not all endpoints need response_model
                pass

    # Check for proper exception handling pattern
    if "try:" in content and "except" in content:
        # Good - has exception handling
        pass

    return errors


def validate_service_content(content: str, file_path: str) -> list:
    """Validate service layer patterns."""
    errors = []

    # Check for repository instantiation in __init__
    if "class " in content and "Service" in content:
        if "__init__" in content:
            init_match = re.search(r'def __init__\s*\(self[^)]*\):\s*\n((?:\s+.+\n)+)', content)
            if init_match:
                init_body = init_match.group(1)
                # Check for repository instantiation
                if "Repository()" in init_body or "_repo = " in init_body:
                    # Good pattern
                    pass

    # Check that session is passed to methods, not stored
    if "self.session" in content or "self._session" in content:
        errors.append({
            "rule": "SERVICE_NO_SESSION_STORAGE",
            "message": "Services should not store session as instance variable",
            "suggestion": "Pass session as parameter to each method instead",
            "severity": "error"
        })

    # Check for proper exception usage
    if "raise HTTPException" in content:
        errors.append({
            "rule": "SERVICE_NO_HTTP_EXCEPTION",
            "message": "Services should raise domain exceptions, not HTTPException",
            "suggestion": "Use NotFoundError, ConflictError, ValidationError instead",
            "severity": "warning"
        })

    return errors


def validate_repository_content(content: str, file_path: str) -> list:
    """Validate repository layer patterns."""
    errors = []

    # Check for async methods
    if "class " in content and "Repository" in content:
        methods = re.findall(r'def (\w+)\s*\(', content)
        async_methods = re.findall(r'async def (\w+)\s*\(', content)

        # Repository methods should be async
        sync_methods = [m for m in methods if m not in async_methods and not m.startswith("_") and m != "__init__"]
        if sync_methods:
            errors.append({
                "rule": "REPOSITORY_ASYNC_METHODS",
                "message": f"Repository methods should be async: {sync_methods}",
                "suggestion": "Add 'async' keyword to repository methods",
                "severity": "warning"
            })

    # Check for session.commit() - should use flush instead
    if "session.commit()" in content or "await session.commit()" in content:
        errors.append({
            "rule": "REPOSITORY_NO_COMMIT",
            "message": "Repository should use flush(), not commit(). Let the session manager handle commits.",
            "suggestion": "Replace session.commit() with session.flush()",
            "severity": "warning"
        })

    return errors


def validate_model_content(content: str, file_path: str) -> list:
    """Validate SQLAlchemy model patterns."""
    errors = []

    # Check for proper Mapped type hints
    if "class " in content and "(Base)" in content:
        # Check for old-style Column definitions without Mapped
        old_column_pattern = r'(\w+)\s*=\s*Column\s*\('
        old_columns = re.findall(old_column_pattern, content)

        if old_columns and "Mapped[" not in content:
            errors.append({
                "rule": "MODEL_USE_MAPPED_TYPE",
                "message": f"Model uses old Column() syntax without Mapped type hints",
                "suggestion": "Use 'field: Mapped[type] = mapped_column(...)' syntax",
                "severity": "warning"
            })

    # Check UUID storage pattern
    if "UUID" in content or "uuid" in content:
        if "CHAR(36)" not in content and "String(36)" not in content:
            if "uuid4" in content:
                errors.append({
                    "rule": "MODEL_UUID_CHAR36",
                    "message": "UUID columns should be stored as CHAR(36) for MySQL/MariaDB",
                    "suggestion": "Use 'mapped_column(CHAR(36), ...)' for UUID storage",
                    "severity": "info"
                })

    return errors


def main():
    """Main validation entry point."""
    tool_input = get_tool_input()
    file_path = tool_input.get("file_path", "")
    new_content = tool_input.get("content", "") or tool_input.get("new_string", "")

    # Skip if not a backend file
    if not file_path or not is_backend_file(file_path):
        sys.exit(0)

    # Skip __init__.py and test files
    if "__init__.py" in file_path or "/tests/" in file_path:
        sys.exit(0)

    all_errors = []

    # Run appropriate validators
    if is_schema_file(file_path):
        all_errors.extend(validate_schema_content(new_content, file_path))

    if is_router_file(file_path):
        all_errors.extend(validate_router_content(new_content, file_path))

    if is_service_file(file_path):
        all_errors.extend(validate_service_content(new_content, file_path))

    if is_repository_file(file_path):
        all_errors.extend(validate_repository_content(new_content, file_path))

    if is_model_file(file_path):
        all_errors.extend(validate_model_content(new_content, file_path))

    # Check for blocking errors
    blocking_errors = [e for e in all_errors if e.get("severity") == "error"]

    if blocking_errors:
        # Output errors and block the write
        result = {
            "decision": "block",
            "reason": f"Pattern violations detected: {len(blocking_errors)} error(s)",
            "errors": blocking_errors
        }
        print(json.dumps(result))
        sys.exit(2)

    # Output warnings but allow the write
    if all_errors:
        result = {
            "decision": "allow",
            "warnings": all_errors
        }
        print(json.dumps(result))

    sys.exit(0)


if __name__ == "__main__":
    main()
