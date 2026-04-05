#!/usr/bin/env python3
"""
Fix repository files that were broken by the initial refactoring script.
"""

import os
import re
from pathlib import Path

REPOSITORIES_DIR = Path("src/backend/api/repositories")

SKIP_FILES = {
    "base.py",
    "__init__.py",
    ".gitkeep",
    "page_repository.py",
    "role_repository.py",
    "role_permission_repository.py",
    "page_permission_repository.py",
}


def fix_repository_file(filepath: Path) -> None:
    """Fix a broken repository file."""
    print(f"Fixing {filepath.name}...")

    with open(filepath, "r") as f:
        content = f.read()

    original_content = content

    # Fix 1: Remove duplicate empty __init__ and misplaced model line
    # Pattern like:
    #     def __init__(self):
    #     model = ModelName
    #     def __init__(self, session: AsyncSession):
    content = re.sub(
        r"\n    def __init__\(self\):\n    model = \w+\n\n    def __init__\(self, session: AsyncSession\):\n",
        "\n",
        content,
    )

    # Fix 2: Remove duplicate session: AsyncSession parameter in method signatures
    # Pattern: async def method_name(self, session: AsyncSession, ...) -> ...
    content = re.sub(
        r"async def (\w+)\(self,\s*session:\s*AsyncSession,\s*",
        r"async def \1(self, ",
        content,
    )

    # Pattern: async def method_name(self, session: AsyncSession) -> ...
    content = re.sub(
        r"async def (\w+)\(self,\s*session:\s*AsyncSession\)\s*->",
        r"async def \1(self) ->",
        content,
    )

    # Fix 3: Replace NotFoundError(entity=..., identifier=...) with message format
    # Pattern: raise NotFoundError(entity="X", identifier=Y)
    content = re.sub(
        r'raise NotFoundError\(entity="([^"]+)",\s*identifier=([^)]+)\)',
        r'raise NotFoundError(f"\1 with ID \2 not found")',
        content,
    )

    # Fix 4: Convert result.scalars().all() to list(result.scalars().all())
    content = re.sub(
        r"return result\.scalars\(\)\.all\(\), total",
        r"return list(result.scalars().all()), total",
        content,
    )

    if content != original_content:
        with open(filepath, "w") as f:
            f.write(content)
        print(f"  Fixed")
    else:
        print(f"  No changes needed")


def main():
    """Main entry point."""
    os.chdir("/home/adel/workspace/employee-meal-request")

    for filepath in REPOSITORIES_DIR.glob("*_repository.py"):
        if filepath.name in SKIP_FILES:
            print(f"Skipping {filepath.name} (already manually fixed)")
            continue

        try:
            fix_repository_file(filepath)
        except Exception as e:
            print(f"  ERROR: {e}")


if __name__ == "__main__":
    main()
