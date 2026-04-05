#!/usr/bin/env python3
"""
Helper script to refactor repositories to inherit from BaseRepository.
This script will help transform repositories by:
1. Adding BaseRepository import and inheritance
2. Updating __init__ to accept session
3. Removing session parameter from all methods
"""

import os
import re
from pathlib import Path

REPOSITORIES_DIR = Path("src/backend/api/repositories")

# Skip these files (special cases)
SKIP_FILES = {"base.py", "__init__.py", ".gitkeep"}

# Files to refactor
REPOS_TO_SKIP = {
    "session_repository.py",
    "hris_repository.py",
}  # Complex logic, handle separately


def get_model_class_name(repo_filename: str) -> str:
    """Extract the model class name from the repository file name."""
    # e.g., "user_repository.py" -> "UserRepository" (current class name)
    # We need to find the model name from the imports or class docstring
    repo_name = repo_filename.replace("_repository.py", "")
    # Common patterns: user -> User, meal_request -> MealRequest, etc.
    parts = repo_name.split("_")
    return "".join(p.capitalize() for p in parts)


def refactor_repository(filepath: Path) -> None:
    """Refactor a single repository file."""
    print(f"Processing {filepath.name}...")

    with open(filepath, "r") as f:
        content = f.read()

    # Skip if already has BaseRepository
    if "from .base import BaseRepository" in content:
        print(f"  Skipping - already refactored")
        return

    # Find model class (look for "from db.models import" line)
    model_match = re.search(r"from db\.models import (.+)", content)
    if not model_match:
        print(f"  Skipping - no db.models import found")
        return

    imports_line = model_match.group(1)
    # Try to find the model class name (usually the first one or based on repo name)
    repo_name = filepath.stem.replace("_repository", "")
    model_name = "".join(p.capitalize() for p in repo_name.split("_"))

    # Check if model_name is in imports
    if model_name not in imports_line:
        # Try to find another candidate
        for imp in imports_line.split(","):
            candidate = imp.strip()
            if candidate.lower().startswith(repo_name.replace("_", "").lower()):
                model_name = candidate
                break
        else:
            print(f"  Skipping - can't determine model for {model_name}")
            return

    # Step 1: Add BaseRepository import
    content = re.sub(
        r"from db\.models import (.+)",
        r"from db.models import \1\nfrom .base import BaseRepository",
        content,
    )

    # Step 2: Update class declaration to inherit from BaseRepository[model_name]
    old_class_decl = f"class {model_name}Repository:"
    new_class_decl = f"class {model_name}Repository(BaseRepository[{model_name}]):"
    content = content.replace(old_class_decl, new_class_decl)

    # Step 3: Add model class attribute and update __init__
    old_init_pattern = r'(class \w+Repository\(BaseRepository\[\w+\]\):\s+""".*?"""\s+def __init__\(self\):)\s*pass'
    new_init = r"""\1
    model = MODEL_NAME

    def __init__(self, session: AsyncSession):
        super().__init__(session)""".replace("MODEL_NAME", model_name)

    content = re.sub(old_init_pattern, new_init, content, flags=re.DOTALL)

    # Step 4: Remove session parameter from all async methods
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

    # Step 5: Replace session usage with self.session in method bodies
    # This is complex - we need to find all uses of `session.` and `await session.`
    # We'll do this carefully by replacing patterns like:
    # - session.add -> self.session.add
    # - session.execute -> self.session.execute
    # - await session.execute -> await self.session.execute
    # - session.get -> self.session.get
    # - session.flush -> self.session.flush
    # - session.rollback -> self.session.rollback
    # - session.delete -> self.session.delete
    # - session.refresh -> self.session.refresh
    # - session.commit -> self.session.commit

    session_patterns = [
        (r"\bsession\.add\b", "self.session.add"),
        (r"\bsession\.execute\b", "self.session.execute"),
        (r"\bsession\.get\b", "self.session.get"),
        (r"\bsession\.flush\b", "self.session.flush"),
        (r"\bsession\.rollback\b", "self.session.rollback"),
        (r"\bsession\.delete\b", "self.session.delete"),
        (r"\bsession\.refresh\b", "self.session.refresh"),
        (r"\bsession\.commit\b", "self.session.commit"),
    ]

    for pattern, replacement in session_patterns:
        content = re.sub(pattern, replacement, content)

    # Write back
    with open(filepath, "w") as f:
        f.write(content)

    print(f"  Done - refactored to use BaseRepository[{model_name}]")


def main():
    """Main entry point."""
    os.chdir("/home/adel/workspace/employee-meal-request")

    for filepath in REPOSITORIES_DIR.glob("*_repository.py"):
        if filepath.name in SKIP_FILES:
            continue
        if filepath.name in REPOS_TO_SKIP:
            print(f"Skipping {filepath.name} (manual review needed)")
            continue

        try:
            refactor_repository(filepath)
        except Exception as e:
            print(f"  ERROR: {e}")


if __name__ == "__main__":
    main()
