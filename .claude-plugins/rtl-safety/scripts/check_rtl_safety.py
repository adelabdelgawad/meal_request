#!/usr/bin/env python3
"""
RTL Layout Safety Hook

Checks React/TSX components for common RTL layout issues that break Arabic layouts.

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

# Only check TSX files in my-app
if "my-app" not in file_path or not file_path.endswith(".tsx"):
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

warnings = []

# Check for directional margins without RTL variant
# ml-X or mr-X without rtl: variant
margin_left_pattern = r'\bml-\d+(?!\s*rtl:)'
margin_right_pattern = r'\bmr-\d+(?!\s*rtl:)'

ml_matches = re.findall(margin_left_pattern, content)
mr_matches = re.findall(margin_right_pattern, content)

# Filter to check if there's an RTL variant nearby
for match in set(ml_matches):
    # Check if there's a corresponding rtl: variant
    if f"rtl:ml-" not in content and "me-" not in content and "ms-" not in content:
        warnings.append(
            f"Found '{match}' without RTL variant. "
            f"Consider using 'me-X' (margin-end) or adding 'rtl:mr-X'."
        )

for match in set(mr_matches):
    if f"rtl:mr-" not in content and "me-" not in content and "ms-" not in content:
        warnings.append(
            f"Found '{match}' without RTL variant. "
            f"Consider using 'ms-X' (margin-start) or adding 'rtl:ml-X'."
        )

# Check for directional padding without RTL variant
pl_pattern = r'\bpl-\d+(?!\s*rtl:)'
pr_pattern = r'\bpr-\d+(?!\s*rtl:)'

pl_matches = re.findall(pl_pattern, content)
pr_matches = re.findall(pr_pattern, content)

for match in set(pl_matches):
    if "pe-" not in content and "ps-" not in content:
        warnings.append(
            f"Found '{match}' without RTL variant. "
            f"Consider using 'pe-X' (padding-end) or adding 'rtl:pr-X'."
        )

for match in set(pr_matches):
    if "pe-" not in content and "ps-" not in content:
        warnings.append(
            f"Found '{match}' without RTL variant. "
            f"Consider using 'ps-X' (padding-start) or adding 'rtl:pl-X'."
        )

# Check for fixed text alignment
text_left = r'text-left(?!\s*rtl:)'
text_right = r'text-right(?!\s*rtl:)'

if re.search(text_left, content):
    warnings.append(
        "Found 'text-left' without RTL variant. "
        "Consider using 'text-start' or adding 'rtl:text-right'."
    )

if re.search(text_right, content):
    warnings.append(
        "Found 'text-right' without RTL variant. "
        "Consider using 'text-end' or adding 'rtl:text-left'."
    )

# Check for flex-row without RTL consideration on icon+text combos
# This is a heuristic - look for Icon components next to text
icon_flex_pattern = r'flex\s+(?:flex-row\s+)?items-center[^>]*>\s*<\w*Icon'
if re.search(icon_flex_pattern, content):
    if "rtl:flex-row-reverse" not in content and "gap-" not in content:
        warnings.append(
            "Found Icon in flex container without gap or RTL handling. "
            "Icons with text should use 'gap-X' or 'rtl:flex-row-reverse'."
        )

# Check for Sheet/Drawer with fixed side
sheet_pattern = r'<Sheet[^>]*side\s*=\s*["\'](?:left|right)["\']'
if re.search(sheet_pattern, content):
    if "isRtl" not in content:
        warnings.append(
            "Found Sheet with fixed side without RTL check. "
            "Use 'side={isRtl ? \"left\" : \"right\"}' for RTL support."
        )

# Check for directional borders
border_l_pattern = r'\bborder-l-\d+(?!\s*rtl:)'
border_r_pattern = r'\bborder-r-\d+(?!\s*rtl:)'

if re.search(border_l_pattern, content):
    warnings.append(
        "Found 'border-l-X' without RTL variant. "
        "Consider using 'border-s-X' (border-start) or adding 'rtl:border-r-X'."
    )

if re.search(border_r_pattern, content):
    warnings.append(
        "Found 'border-r-X' without RTL variant. "
        "Consider using 'border-e-X' (border-end) or adding 'rtl:border-l-X'."
    )

# Check for directional rounded corners (except rounded-full)
rounded_l_pattern = r'\brounded-l-(?!full)'
rounded_r_pattern = r'\brounded-r-(?!full)'

if re.search(rounded_l_pattern, content):
    if "rtl:rounded-" not in content:
        warnings.append(
            "Found directional rounded corners without RTL variant. "
            "Add 'rtl:rounded-r-X rtl:rounded-l-none' for RTL support."
        )

if re.search(rounded_r_pattern, content):
    if "rtl:rounded-" not in content:
        warnings.append(
            "Found directional rounded corners without RTL variant. "
            "Add 'rtl:rounded-l-X rtl:rounded-r-none' for RTL support."
        )

# Limit warnings to first 5 unique issues
unique_warnings = list(dict.fromkeys(warnings))[:5]

# Report warnings
if unique_warnings:
    print("\n" + "=" * 60)
    print("RTL LAYOUT SAFETY WARNING")
    print("=" * 60)
    print(f"\nFile: {file_path}")

    print("\nPotential RTL Issues:")
    for i, warning in enumerate(unique_warnings, 1):
        print(f"  {i}. {warning}")

    print("\nRTL-Safe Alternatives:")
    print("""
    Physical → Logical Properties:
    - ml-X → ms-X (margin-start)
    - mr-X → me-X (margin-end)
    - pl-X → ps-X (padding-start)
    - pr-X → pe-X (padding-end)
    - text-left → text-start
    - text-right → text-end
    - border-l → border-s
    - border-r → border-e

    Or use RTL variants:
    - ml-2 rtl:ml-0 rtl:mr-2
    - flex-row rtl:flex-row-reverse
    """)
    print("=" * 60 + "\n")

sys.exit(0)
