#!/usr/bin/env python3
"""
CamelModel Enforcement Hook

Checks that Pydantic schemas in api/schemas/ inherit from CamelModel,
not BaseModel directly. This ensures camelCase JSON serialization for
frontend compatibility.

Runs as a PostToolUse hook after Write/Edit operations.
"""

import os
import sys
import re
import json

# Read environment variables from Claude Code
tool_use_id = os.environ.get("CLAUDE_TOOL_USE_ID", "")
tool_use_name = os.environ.get("CLAUDE_TOOL_USE_NAME", "")
tool_use_input = os.environ.get("CLAUDE_TOOL_USE_INPUT", "{}")
tool_use_output = os.environ.get("CLAUDE_TOOL_USE_OUTPUT", "")

# Only check schema files
try:
    input_data = json.loads(tool_use_input)
    file_path = input_data.get("file_path", "")
except (json.JSONDecodeError, TypeError):
    file_path = ""

# Skip if not a schema file
if "api/schemas" not in file_path or not file_path.endswith(".py"):
    sys.exit(0)

# Skip _base.py (it defines CamelModel)
if file_path.endswith("_base.py"):
    sys.exit(0)

# Check if file exists
if not os.path.exists(file_path):
    sys.exit(0)

# Read the file
try:
    with open(file_path, "r") as f:
        content = f.read()
except Exception as e:
    print(f"Error reading {file_path}: {e}", file=sys.stderr)
    sys.exit(0)

# Patterns to detect violations
issues = []

# Check for classes inheriting from BaseModel directly
basemodel_pattern = r'class\s+(\w+)\s*\(\s*BaseModel\s*\)'
matches = re.findall(basemodel_pattern, content)

if matches:
    for class_name in matches:
        issues.append(f"Class '{class_name}' inherits from BaseModel instead of CamelModel")

# Check for manual alias_generator
if "alias_generator" in content and "CamelModel" not in content:
    issues.append("Found alias_generator but no CamelModel import - use CamelModel instead")

# Check for Field(alias=...) for camelCase conversion
alias_pattern = r'Field\s*\([^)]*alias\s*=\s*["\']([a-z]+[A-Z][a-zA-Z]*)["\']'
alias_matches = re.findall(alias_pattern, content)
if alias_matches:
    for alias in alias_matches:
        issues.append(f"Found manual alias '{alias}' - CamelModel handles camelCase conversion automatically")

# Check for missing CamelModel import when classes exist
class_pattern = r'class\s+\w+\s*\('
has_classes = re.search(class_pattern, content)
has_camelmodel_import = "from api.schemas._base import CamelModel" in content or "from api.schemas._base import" in content and "CamelModel" in content

if has_classes and not has_camelmodel_import:
    # Check if any class inherits from CamelModel
    inherits_camelmodel = re.search(r'class\s+\w+\s*\(\s*CamelModel', content)
    if not inherits_camelmodel:
        issues.append("Schema file has classes but no CamelModel import")

# Report issues
if issues:
    print("\n" + "=" * 60)
    print("CAMELMODEL ENFORCEMENT WARNING")
    print("=" * 60)
    print(f"\nFile: {file_path}")
    print("\nIssues found:")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
    print("\nReminder: All Pydantic schemas must inherit from CamelModel")
    print("to ensure camelCase JSON serialization for frontend compatibility.")
    print("\nCorrect pattern:")
    print("  from api.schemas._base import CamelModel")
    print("")
    print("  class MySchema(CamelModel):")
    print("      field_name: str  # Auto-converts to 'fieldName' in JSON")
    print("=" * 60 + "\n")

sys.exit(0)  # Always exit successfully (advisory only)
