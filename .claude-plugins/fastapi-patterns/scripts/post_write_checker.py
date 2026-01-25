#!/usr/bin/env python3
"""
Post-write checker for FastAPI backend patterns.

This script runs AFTER a file is written to provide feedback
and suggestions for improvement. It doesn't block writes.

Exit codes:
  0 - Success (feedback provided via stdout)
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


def check_imports(content: str, file_path: str) -> list:
    """Check for proper import patterns."""
    suggestions = []

    # Schema files should import CamelModel
    if "schemas" in file_path and file_path.endswith(".py"):
        if "class " in content and "CamelModel" in content:
            if "from api.schemas._base import CamelModel" not in content:
                suggestions.append({
                    "type": "import",
                    "message": "Consider using 'from api.schemas._base import CamelModel'",
                    "file": file_path
                })

    # Check for proper typing imports
    if "List[" in content or "Optional[" in content or "Dict[" in content:
        if "from typing import" not in content:
            suggestions.append({
                "type": "import",
                "message": "Add 'from typing import List, Optional, Dict' for type hints",
                "file": file_path
            })

    return suggestions


def check_docstrings(content: str, file_path: str) -> list:
    """Check for missing docstrings."""
    suggestions = []

    # Check class docstrings
    class_pattern = r'class\s+(\w+)[^:]*:\s*\n(\s+)(?!"""|\'\'\')(\w)'
    missing_class_docs = re.findall(class_pattern, content)

    for class_name, _, _ in missing_class_docs:
        if not class_name.startswith("_"):
            suggestions.append({
                "type": "documentation",
                "message": f"Class '{class_name}' is missing a docstring",
                "file": file_path
            })

    # Check function docstrings for public methods
    func_pattern = r'(async\s+)?def\s+(\w+)\s*\([^)]*\)[^:]*:\s*\n(\s+)(?!"""|\'\'\')(\w)'
    functions = re.findall(func_pattern, content)

    for _, func_name, _, _ in functions:
        if not func_name.startswith("_"):
            suggestions.append({
                "type": "documentation",
                "message": f"Function '{func_name}' is missing a docstring",
                "file": file_path
            })

    return suggestions


def check_error_handling(content: str, file_path: str) -> list:
    """Check for proper error handling patterns."""
    suggestions = []

    # Check for bare except clauses
    if re.search(r'except\s*:', content):
        suggestions.append({
            "type": "error_handling",
            "message": "Avoid bare 'except:' clauses. Catch specific exceptions.",
            "file": file_path
        })

    # Check for pass in except blocks
    if re.search(r'except[^:]*:\s*\n\s+pass', content):
        suggestions.append({
            "type": "error_handling",
            "message": "Avoid 'pass' in except blocks. Log or handle the error.",
            "file": file_path
        })

    return suggestions


def check_async_patterns(content: str, file_path: str) -> list:
    """Check for proper async/await patterns."""
    suggestions = []

    # Check for missing await on async calls
    async_calls = [
        "session.execute",
        "session.flush",
        "session.commit",
        "session.rollback",
        "session.refresh",
        "clientApi.get",
        "clientApi.post",
        "clientApi.put",
        "clientApi.delete",
    ]

    for call in async_calls:
        # Pattern: call without await before it
        pattern = rf'(?<!await\s){re.escape(call)}\s*\('
        if re.search(pattern, content):
            # Check if it's actually missing await
            if f"await {call}" not in content:
                suggestions.append({
                    "type": "async",
                    "message": f"'{call}' should be awaited",
                    "file": file_path
                })

    return suggestions


def main():
    """Main checker entry point."""
    tool_input = get_tool_input()
    file_path = tool_input.get("file_path", "")

    # Skip if not a backend file
    if not file_path or not is_backend_file(file_path):
        sys.exit(0)

    # Skip test files and __init__.py
    if "/tests/" in file_path or "__init__.py" in file_path:
        sys.exit(0)

    # Read the written file
    try:
        content = Path(file_path).read_text()
    except Exception:
        sys.exit(0)

    all_suggestions = []

    # Run checkers
    all_suggestions.extend(check_imports(content, file_path))
    all_suggestions.extend(check_docstrings(content, file_path))
    all_suggestions.extend(check_error_handling(content, file_path))
    all_suggestions.extend(check_async_patterns(content, file_path))

    # Output suggestions (limited to top 5 to avoid noise)
    if all_suggestions:
        output = {
            "status": "suggestions",
            "count": len(all_suggestions),
            "suggestions": all_suggestions[:5]
        }
        print(json.dumps(output, indent=2))

    sys.exit(0)


if __name__ == "__main__":
    main()
