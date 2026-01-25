#!/usr/bin/env python3
"""
Repository Pattern Enforcement Hook

Checks that code follows the 3-layer architecture:
- Routers: Thin, handle HTTP concerns only
- Services: Business logic and orchestration
- Repositories: Data access only

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

# Only check relevant files
if not file_path.endswith(".py"):
    sys.exit(0)

is_router = "api/v1/" in file_path and "router" in file_path
is_service = "api/services/" in file_path
is_repository = "api/repositories/" in file_path

# Skip if not in our target directories
if not (is_router or is_service or is_repository):
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

issues = []
warnings = []

# Check Router violations
if is_router:
    # Check for direct database operations
    if re.search(r'select\s*\(', content, re.IGNORECASE):
        issues.append("Router contains SQLAlchemy select() - move to repository")

    if re.search(r'session\.execute\s*\(', content):
        issues.append("Router executes queries directly - use service layer")

    if re.search(r'session\.add\s*\(', content):
        issues.append("Router adds to session directly - use service layer")

    if re.search(r'session\.commit\s*\(', content):
        issues.append("Router commits directly - use service layer")

    # Check for business logic indicators
    if content.count("if ") > 10:
        warnings.append("Router has many conditionals - consider moving logic to service")

# Check Service violations
if is_service:
    # Check for HTTP concerns
    if "HTTPException" in content:
        # This is actually OK in services for validation errors
        pass

    if re.search(r'@router\.(get|post|put|delete|patch)', content):
        issues.append("Service contains route decorators - services should not define routes")

    # Check for raw SQL without going through repository
    if re.search(r'session\.execute\s*\(\s*text\s*\(', content):
        warnings.append("Service uses raw SQL - consider using repository method")

# Check Repository violations
if is_repository:
    # Check for business logic
    if "HTTPException" in content:
        issues.append("Repository raises HTTPException - use domain exceptions instead")

    # Check for service imports
    if re.search(r'from\s+api\.services\s+import', content):
        issues.append("Repository imports from services - repositories should not depend on services")

    # Check for external API calls
    if "httpx" in content or "requests" in content:
        issues.append("Repository makes HTTP calls - external calls belong in services")

    # Check for business logic patterns
    if re.search(r'if\s+.*\.is_admin', content) or re.search(r'if\s+.*\.is_super_admin', content):
        issues.append("Repository checks admin status - permission checks belong in services")

# Report issues
if issues or warnings:
    layer = "Router" if is_router else "Service" if is_service else "Repository"

    print("\n" + "=" * 60)
    print(f"REPOSITORY PATTERN WARNING ({layer})")
    print("=" * 60)
    print(f"\nFile: {file_path}")

    if issues:
        print("\nVIOLATIONS:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")

    if warnings:
        print("\nWARNINGS:")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")

    print("\nArchitecture Layers:")
    print("""
    Router (api/v1/)
    ├── Handle HTTP request/response
    ├── Parse parameters and body
    ├── Call service methods
    └── Return response models

    Service (api/services/)
    ├── Business logic
    ├── Orchestrate multiple repositories
    ├── Raise HTTPException for errors
    └── Audit logging

    Repository (api/repositories/)
    ├── Database operations only
    ├── CRUD methods
    ├── Query building
    └── No business logic
    """)
    print("=" * 60 + "\n")

sys.exit(0)
