#!/usr/bin/env python3
"""
Validate a data table page follows the established patterns.

Usage:
    python validate-table-page.py <page-directory>
    python validate-table-page.py src/my-app/app/(pages)/users
    python validate-table-page.py src/my-app/app/(pages)/users --verbose
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import NamedTuple


class CheckResult(NamedTuple):
    passed: bool
    message: str
    details: str = ""


def check_file_exists(path: Path, description: str) -> CheckResult:
    """Check if a file exists."""
    if path.exists():
        return CheckResult(True, f"✓ {description} exists")
    return CheckResult(False, f"✗ {description} missing", str(path))


def check_content_pattern(
    path: Path,
    pattern: str,
    description: str,
    required: bool = True
) -> CheckResult:
    """Check if file contains a pattern."""
    if not path.exists():
        return CheckResult(not required, f"- {description} (file not found)")

    content = path.read_text()
    if re.search(pattern, content):
        return CheckResult(True, f"✓ {description}")
    return CheckResult(
        not required,
        f"{'✗' if required else '⚠'} {description}",
        f"Pattern not found: {pattern[:50]}..."
    )


def check_no_pattern(
    path: Path,
    pattern: str,
    description: str
) -> CheckResult:
    """Check that file does NOT contain a pattern."""
    if not path.exists():
        return CheckResult(True, f"- {description} (file not found)")

    content = path.read_text()
    if re.search(pattern, content):
        return CheckResult(False, f"✗ {description}", f"Found: {pattern[:50]}...")
    return CheckResult(True, f"✓ {description}")


def validate_page(page_dir: Path, verbose: bool = False) -> tuple[int, int]:
    """Validate a data table page directory."""
    results: list[CheckResult] = []

    # Extract feature name from directory
    feature = page_dir.name

    # === Structure Checks ===
    print("\n=== Structure Checks ===")

    results.append(check_file_exists(
        page_dir / "page.tsx",
        "page.tsx (server component)"
    ))

    table_dir = page_dir / "_components" / "table"
    results.append(check_file_exists(
        table_dir / f"{feature}-table.tsx",
        f"{feature}-table.tsx (SWR wrapper)"
    ))

    context_dir = page_dir / "context"
    context_files = list(context_dir.glob("*-context.tsx")) if context_dir.exists() else []
    if context_files:
        results.append(CheckResult(True, "✓ Context file exists"))
    else:
        results.append(CheckResult(False, "✗ Context file missing"))

    # === page.tsx Checks ===
    page_file = page_dir / "page.tsx"
    print("\n=== page.tsx Checks ===")

    results.append(check_no_pattern(
        page_file,
        r'"use client"',
        "page.tsx is Server Component (no 'use client')"
    ))

    results.append(check_content_pattern(
        page_file,
        r'export\s+default\s+async\s+function',
        "page.tsx has async function export"
    ))

    results.append(check_content_pattern(
        page_file,
        r'await\s+searchParams',
        "page.tsx awaits searchParams (Next.js 15+)"
    ))

    results.append(check_content_pattern(
        page_file,
        r'initialData=',
        "page.tsx passes initialData to client component"
    ))

    # === Table Component Checks ===
    table_file = table_dir / f"{feature}-table.tsx"
    print(f"\n=== {feature}-table.tsx Checks ===")

    results.append(check_content_pattern(
        table_file,
        r'"use client"',
        "Table component has 'use client'"
    ))

    results.append(check_content_pattern(
        table_file,
        r'useSWR\s*<',
        "Table uses useSWR hook"
    ))

    results.append(check_content_pattern(
        table_file,
        r'fallbackData:\s*initialData',
        "SWR uses fallbackData from props"
    ))

    results.append(check_content_pattern(
        table_file,
        r'keepPreviousData:\s*true',
        "SWR has keepPreviousData: true"
    ))

    results.append(check_content_pattern(
        table_file,
        r'revalidateOnMount:\s*false',
        "SWR has revalidateOnMount: false"
    ))

    results.append(check_content_pattern(
        table_file,
        r'revalidateOnFocus:\s*false',
        "SWR has revalidateOnFocus: false"
    ))

    # Cache update function
    results.append(check_content_pattern(
        table_file,
        r'const\s+update\w+\s*=\s*async',
        "Has cache update function (updateItems/updateUsers/etc)"
    ))

    results.append(check_content_pattern(
        table_file,
        r'revalidate:\s*false',
        "Cache update uses revalidate: false"
    ))

    # Loading state
    results.append(check_content_pattern(
        table_file,
        r'useState<Set<string>>',
        "Has updatingIds state (loading tracking)"
    ))

    results.append(check_content_pattern(
        table_file,
        r'markUpdating',
        "Has markUpdating function"
    ))

    results.append(check_content_pattern(
        table_file,
        r'clearUpdating',
        "Has clearUpdating function"
    ))

    # Context provider
    results.append(check_content_pattern(
        table_file,
        r'Provider\s*>',
        "Wraps children with context Provider"
    ))

    # === Column Definitions Checks ===
    columns_file = table_dir / f"{feature}-table-columns.tsx"
    print(f"\n=== {feature}-table-columns.tsx Checks ===")

    if columns_file.exists():
        results.append(check_content_pattern(
            columns_file,
            r'export\s+function\s+create\w+Columns',
            "Has column factory function"
        ))

        results.append(check_content_pattern(
            columns_file,
            r'updatingIds',
            "Columns receive updatingIds"
        ))

        results.append(check_content_pattern(
            columns_file,
            r'markUpdating',
            "Columns receive markUpdating"
        ))

        results.append(check_content_pattern(
            columns_file,
            r'clearUpdating',
            "Columns receive clearUpdating"
        ))
    else:
        results.append(CheckResult(False, "✗ Columns file missing"))

    # === Context Checks ===
    print("\n=== Context Checks ===")

    if context_files:
        context_file = context_files[0]
        results.append(check_content_pattern(
            context_file,
            r'createContext',
            "Uses createContext"
        ))

        results.append(check_content_pattern(
            context_file,
            r'useContext',
            "Has useContext hook"
        ))

        results.append(check_content_pattern(
            context_file,
            r'update\w+.*Promise<void>',
            "Context has update function type"
        ))

    # === Print Results ===
    print("\n" + "=" * 50)
    print("VALIDATION RESULTS")
    print("=" * 50)

    passed = 0
    failed = 0

    for result in results:
        print(result.message)
        if verbose and result.details:
            print(f"    {result.details}")

        if result.passed:
            passed += 1
        else:
            failed += 1

    print(f"\nPassed: {passed}, Failed: {failed}")

    return passed, failed


def main():
    parser = argparse.ArgumentParser(
        description="Validate a data table page"
    )
    parser.add_argument(
        "page_dir",
        help="Path to page directory"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed error information"
    )

    args = parser.parse_args()

    page_dir = Path(args.page_dir)

    if not page_dir.exists():
        print(f"Error: Directory not found: {page_dir}")
        sys.exit(1)

    if not page_dir.is_dir():
        print(f"Error: Not a directory: {page_dir}")
        sys.exit(1)

    print(f"Validating: {page_dir}")

    passed, failed = validate_page(page_dir, args.verbose)

    if failed > 0:
        print("\n⚠️  Some checks failed. Review the patterns in PATTERNS.md")
        sys.exit(1)
    else:
        print("\n✓ All checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
