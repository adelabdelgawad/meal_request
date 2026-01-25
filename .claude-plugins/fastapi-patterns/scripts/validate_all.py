#!/usr/bin/env python3
"""
Comprehensive validation script for the entire backend codebase.

Usage:
    python validate_all.py [--path PATH] [--fix] [--verbose]

Validates:
    - Schema files inherit from CamelModel
    - Routers follow dependency injection patterns
    - Services don't store sessions
    - Repositories use async methods
    - Models use Mapped type hints
    - Project structure follows conventions
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class ValidationResult:
    """Result of a validation check."""
    file: str
    rule: str
    severity: str  # error, warning, info
    message: str
    line: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationReport:
    """Complete validation report."""
    results: List[ValidationResult] = field(default_factory=list)
    files_checked: int = 0
    errors: int = 0
    warnings: int = 0
    info: int = 0

    def add(self, result: ValidationResult):
        self.results.append(result)
        if result.severity == "error":
            self.errors += 1
        elif result.severity == "warning":
            self.warnings += 1
        else:
            self.info += 1


def find_python_files(base_path: Path, subdir: str) -> List[Path]:
    """Find all Python files in a subdirectory."""
    target = base_path / subdir
    if not target.exists():
        return []
    return list(target.rglob("*.py"))


def validate_schema_file(file_path: Path, content: str) -> List[ValidationResult]:
    """Validate a Pydantic schema file."""
    results = []
    file_str = str(file_path)

    # Skip base file
    if "_base.py" in file_str:
        return results

    lines = content.split("\n")

    # Find all class definitions
    for i, line in enumerate(lines, 1):
        class_match = re.match(r'class\s+(\w+)\s*\(([\w\s,\.]+)\)', line)
        if class_match:
            class_name = class_match.group(1)
            bases = class_match.group(2).replace(" ", "").split(",")

            # Check if it's a schema class (by naming convention)
            is_schema = any(suffix in class_name for suffix in
                          ["Create", "Update", "Response", "Base", "Request", "Schema"])

            if is_schema and "BaseModel" in bases and "CamelModel" not in bases:
                results.append(ValidationResult(
                    file=file_str,
                    rule="SCHEMA_CAMEL_MODEL",
                    severity="error",
                    message=f"Class '{class_name}' should inherit from CamelModel, not BaseModel",
                    line=i,
                    suggestion=f"Change to: class {class_name}(CamelModel)"
                ))

    # Check for manual alias_generator
    if "alias_generator" in content and "_base.py" not in file_str:
        for i, line in enumerate(lines, 1):
            if "alias_generator" in line:
                results.append(ValidationResult(
                    file=file_str,
                    rule="SCHEMA_NO_ALIAS_GENERATOR",
                    severity="warning",
                    message="Manual alias_generator found. CamelModel handles this automatically.",
                    line=i,
                    suggestion="Remove alias_generator and use CamelModel"
                ))
                break

    return results


def validate_router_file(file_path: Path, content: str) -> List[ValidationResult]:
    """Validate a FastAPI router file."""
    results = []
    file_str = str(file_path)
    lines = content.split("\n")

    # Check for router definition
    has_router = "APIRouter" in content or "router = " in content

    if not has_router:
        return results

    # Check for proper dependency injection
    has_endpoints = "@router." in content
    has_session_dep = "Depends(get_session)" in content or "Depends(get_maria_session)" in content

    if has_endpoints and not has_session_dep:
        # Check if any endpoint might need session
        if "session" in content.lower() or "Session" in content:
            results.append(ValidationResult(
                file=file_str,
                rule="ROUTER_SESSION_DEPENDENCY",
                severity="warning",
                message="Router may be missing Depends(get_session) for database access",
                suggestion="Add 'session: AsyncSession = Depends(get_session)' to endpoints"
            ))

    # Check for direct HTTPException in business logic
    for i, line in enumerate(lines, 1):
        if "raise HTTPException" in line:
            # Check context - is it in a dependency or main logic?
            results.append(ValidationResult(
                file=file_str,
                rule="ROUTER_HTTP_EXCEPTION",
                severity="info",
                message="HTTPException found. Consider using domain exceptions for reusability.",
                line=i
            ))

    return results


def validate_service_file(file_path: Path, content: str) -> List[ValidationResult]:
    """Validate a service layer file."""
    results = []
    file_str = str(file_path)
    lines = content.split("\n")

    # Check for session storage
    for i, line in enumerate(lines, 1):
        if re.search(r'self\._?session\s*=', line):
            results.append(ValidationResult(
                file=file_str,
                rule="SERVICE_NO_SESSION_STORAGE",
                severity="error",
                message="Services should not store session as instance attribute",
                line=i,
                suggestion="Pass session as parameter to each method"
            ))

    # Check for HTTPException usage
    for i, line in enumerate(lines, 1):
        if "raise HTTPException" in line:
            results.append(ValidationResult(
                file=file_str,
                rule="SERVICE_DOMAIN_EXCEPTIONS",
                severity="warning",
                message="Services should raise domain exceptions, not HTTPException",
                line=i,
                suggestion="Use NotFoundError, ConflictError, ValidationError instead"
            ))

    return results


def validate_repository_file(file_path: Path, content: str) -> List[ValidationResult]:
    """Validate a repository file."""
    results = []
    file_str = str(file_path)
    lines = content.split("\n")

    # Check for commit() usage
    for i, line in enumerate(lines, 1):
        if "session.commit()" in line or "await session.commit()" in line:
            results.append(ValidationResult(
                file=file_str,
                rule="REPOSITORY_NO_COMMIT",
                severity="warning",
                message="Repository should use flush(), not commit()",
                line=i,
                suggestion="Replace with session.flush()"
            ))

    # Check that public methods are async
    in_class = False
    for i, line in enumerate(lines, 1):
        if re.match(r'class\s+\w+Repository', line):
            in_class = True
        elif in_class and re.match(r'\s+def\s+(?!__)\w+', line):
            if "async def" not in line:
                method_match = re.search(r'def\s+(\w+)', line)
                if method_match:
                    method_name = method_match.group(1)
                    results.append(ValidationResult(
                        file=file_str,
                        rule="REPOSITORY_ASYNC_METHODS",
                        severity="warning",
                        message=f"Repository method '{method_name}' should be async",
                        line=i,
                        suggestion=f"Change to: async def {method_name}(...)"
                    ))

    return results


def validate_model_file(file_path: Path, content: str) -> List[ValidationResult]:
    """Validate SQLAlchemy model file."""
    results = []
    file_str = str(file_path)
    lines = content.split("\n")

    # Check for old-style Column without Mapped
    has_mapped = "Mapped[" in content
    has_old_column = re.search(r'\w+\s*=\s*Column\s*\(', content)

    if has_old_column and not has_mapped:
        for i, line in enumerate(lines, 1):
            if re.search(r'\w+\s*=\s*Column\s*\(', line):
                results.append(ValidationResult(
                    file=file_str,
                    rule="MODEL_USE_MAPPED",
                    severity="warning",
                    message="Use Mapped type hints with mapped_column()",
                    line=i,
                    suggestion="Change to: field: Mapped[type] = mapped_column(...)"
                ))
                break  # Only report once

    return results


def validate_project_structure(base_path: Path) -> List[ValidationResult]:
    """Validate overall project structure."""
    results = []

    expected_dirs = [
        "api/v1",
        "api/schemas",
        "api/services",
        "api/repositories",
        "db",
        "core",
        "utils",
    ]

    for dir_path in expected_dirs:
        full_path = base_path / dir_path
        if not full_path.exists():
            results.append(ValidationResult(
                file=str(base_path),
                rule="STRUCTURE_DIRECTORY",
                severity="info",
                message=f"Expected directory not found: {dir_path}"
            ))

    # Check for _base.py in schemas
    base_schema = base_path / "api" / "schemas" / "_base.py"
    if not base_schema.exists():
        results.append(ValidationResult(
            file=str(base_path),
            rule="STRUCTURE_CAMEL_MODEL",
            severity="error",
            message="Missing api/schemas/_base.py with CamelModel definition"
        ))

    return results


def run_validation(base_path: Path, verbose: bool = False) -> ValidationReport:
    """Run all validations and return report."""
    report = ValidationReport()

    # Validate project structure
    report.results.extend(validate_project_structure(base_path))

    # Validate schema files
    for file_path in find_python_files(base_path, "api/schemas"):
        report.files_checked += 1
        try:
            content = file_path.read_text()
            results = validate_schema_file(file_path, content)
            for r in results:
                report.add(r)
        except Exception as e:
            if verbose:
                print(f"Error reading {file_path}: {e}", file=sys.stderr)

    # Validate router files
    for file_path in find_python_files(base_path, "api/v1"):
        report.files_checked += 1
        try:
            content = file_path.read_text()
            results = validate_router_file(file_path, content)
            for r in results:
                report.add(r)
        except Exception as e:
            if verbose:
                print(f"Error reading {file_path}: {e}", file=sys.stderr)

    # Validate service files
    for file_path in find_python_files(base_path, "api/services"):
        report.files_checked += 1
        try:
            content = file_path.read_text()
            results = validate_service_file(file_path, content)
            for r in results:
                report.add(r)
        except Exception as e:
            if verbose:
                print(f"Error reading {file_path}: {e}", file=sys.stderr)

    # Validate repository files
    for file_path in find_python_files(base_path, "api/repositories"):
        report.files_checked += 1
        try:
            content = file_path.read_text()
            results = validate_repository_file(file_path, content)
            for r in results:
                report.add(r)
        except Exception as e:
            if verbose:
                print(f"Error reading {file_path}: {e}", file=sys.stderr)

    # Validate model files
    for file_path in find_python_files(base_path, "db"):
        if "models" in file_path.name:
            report.files_checked += 1
            try:
                content = file_path.read_text()
                results = validate_model_file(file_path, content)
                for r in results:
                    report.add(r)
            except Exception as e:
                if verbose:
                    print(f"Error reading {file_path}: {e}", file=sys.stderr)

    return report


def print_report(report: ValidationReport, verbose: bool = False):
    """Print validation report."""
    print("\n" + "=" * 60)
    print("FASTAPI BACKEND VALIDATION REPORT")
    print("=" * 60)

    print(f"\nFiles checked: {report.files_checked}")
    print(f"Errors: {report.errors}")
    print(f"Warnings: {report.warnings}")
    print(f"Info: {report.info}")

    if report.results:
        print("\n" + "-" * 60)
        print("FINDINGS")
        print("-" * 60)

        # Group by severity
        for severity in ["error", "warning", "info"]:
            items = [r for r in report.results if r.severity == severity]
            if items:
                icon = {"error": "[X]", "warning": "[!]", "info": "[i]"}[severity]
                print(f"\n{severity.upper()}S ({len(items)}):")
                for r in items:
                    location = f"{r.file}"
                    if r.line:
                        location += f":{r.line}"
                    print(f"  {icon} [{r.rule}] {r.message}")
                    print(f"      File: {location}")
                    if r.suggestion and verbose:
                        print(f"      Fix: {r.suggestion}")

    print("\n" + "=" * 60)
    if report.errors > 0:
        print("RESULT: FAILED - Fix errors before committing")
        return 1
    elif report.warnings > 0:
        print("RESULT: PASSED WITH WARNINGS - Consider fixing warnings")
        return 0
    else:
        print("RESULT: PASSED - All patterns followed correctly")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Validate FastAPI backend patterns")
    parser.add_argument(
        "--path",
        default="src/backend",
        help="Path to backend directory (default: src/backend)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output including suggestions"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    base_path = Path(args.path)
    if not base_path.exists():
        print(f"Error: Path not found: {base_path}", file=sys.stderr)
        sys.exit(1)

    report = run_validation(base_path, args.verbose)

    if args.json:
        import json
        output = {
            "files_checked": report.files_checked,
            "errors": report.errors,
            "warnings": report.warnings,
            "info": report.info,
            "results": [
                {
                    "file": r.file,
                    "rule": r.rule,
                    "severity": r.severity,
                    "message": r.message,
                    "line": r.line,
                    "suggestion": r.suggestion
                }
                for r in report.results
            ]
        }
        print(json.dumps(output, indent=2))
        sys.exit(1 if report.errors > 0 else 0)
    else:
        exit_code = print_report(report, args.verbose)
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
