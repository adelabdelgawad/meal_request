#!/usr/bin/env python3
"""
Audit Logging Completeness Hook

Checks that service methods that perform mutations include audit logging calls.
This is important for compliance and traceability.

Runs as a PostToolUse hook after Write/Edit operations.
"""

import os
import sys
import re
import json

# Read environment variables
tool_use_input = os.environ.get("CLAUDE_TOOL_USE_INPUT", "{}")

try:
    input_data = json.loads(tool_use_input)
    file_path = input_data.get("file_path", "")
except (json.JSONDecodeError, TypeError):
    file_path = ""

# Only check service files
if "api/services/" not in file_path or not file_path.endswith(".py"):
    sys.exit(0)

# Skip log service files (they are the audit loggers)
if "log_" in os.path.basename(file_path):
    sys.exit(0)

# Skip __init__.py
if file_path.endswith("__init__.py"):
    sys.exit(0)

# Check if file exists
if not os.path.exists(file_path):
    sys.exit(0)

# Read the file
try:
    with open(file_path, "r") as f:
        content = f.read()
except Exception as e:
    sys.exit(0)

# Sensitive entities that require audit logging
SENSITIVE_ENTITIES = [
    "user",
    "role",
    "permission",
    "page_permission",
    "role_permission",
]

warnings = []

# Find mutation methods (create, update, delete patterns)
mutation_patterns = [
    (r'async\s+def\s+(create_\w+)\s*\(', "create"),
    (r'async\s+def\s+(update_\w+)\s*\(', "update"),
    (r'async\s+def\s+(delete_\w+)\s*\(', "delete"),
    (r'async\s+def\s+(assign_\w+)\s*\(', "assign"),
    (r'async\s+def\s+(revoke_\w+)\s*\(', "revoke"),
    (r'async\s+def\s+(toggle_\w+)\s*\(', "toggle"),
    (r'async\s+def\s+(activate_\w+)\s*\(', "activate"),
    (r'async\s+def\s+(deactivate_\w+)\s*\(', "deactivate"),
]

# Find all mutation methods
mutation_methods = []
for pattern, action_type in mutation_patterns:
    matches = re.finditer(pattern, content)
    for match in matches:
        method_name = match.group(1)
        # Check if it's for a sensitive entity
        for entity in SENSITIVE_ENTITIES:
            if entity in method_name.lower():
                mutation_methods.append((method_name, action_type, entity, match.start()))
                break

# For each mutation method, check if it has audit logging
for method_name, action_type, entity, start_pos in mutation_methods:
    # Find the method body (rough approximation)
    method_pattern = rf'async\s+def\s+{method_name}\s*\([^)]*\)[^:]*:(.+?)(?=\n    async\s+def\s|\n    def\s|\nclass\s|\Z)'
    method_match = re.search(method_pattern, content, re.DOTALL)

    if method_match:
        method_body = method_match.group(1)

        # Check for log service calls
        has_logging = (
            "_log_service" in method_body or
            "LogService" in method_body or
            "log_" in method_body.lower() or
            ".log(" in method_body
        )

        if not has_logging:
            warnings.append(
                f"Method '{method_name}' modifies {entity} but has no audit logging. "
                f"Consider adding log service call for compliance."
            )

# Check for log service import/initialization
has_log_service = (
    "_log_service" in content or
    "LogService" in content or
    "from api.services.log_" in content
)

# If file has mutations but no log service
if mutation_methods and not has_log_service:
    warnings.insert(0, "Service has mutation methods but no log service imported/initialized.")

# Report warnings
if warnings:
    print("\n" + "=" * 60)
    print("AUDIT LOGGING WARNING")
    print("=" * 60)
    print(f"\nFile: {file_path}")

    print("\nWARNINGS:")
    for i, warning in enumerate(warnings, 1):
        print(f"  {i}. {warning}")

    print("\nAudit logging pattern:")
    print("""
    from api.services.log_user_service import LogUserService

    class UserService:
        def __init__(self):
            self._repo = UserRepository()
            self._log_service = LogUserService()

        async def create_user(self, session, data, created_by_id):
            # Create user
            user = await self._repo.create(session, User(**data))

            # Audit log
            await self._log_service.log_create(
                session,
                user_id=str(user.id),
                created_by_id=created_by_id,
                details={"username": user.username},
            )

            return user
    """)
    print("=" * 60 + "\n")

sys.exit(0)
