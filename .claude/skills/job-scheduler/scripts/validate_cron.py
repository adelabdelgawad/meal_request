#!/usr/bin/env python3
"""
Validate cron expressions for the Job Scheduler.

Usage:
    python validate_cron.py "0 2 * * *"
    python validate_cron.py --explain "*/15 * * * *"
    python validate_cron.py --next 5 "0 9 * * 1-5"
"""

import argparse
import sys
from datetime import datetime, timezone


def validate_cron(expression: str) -> tuple[bool, str]:
    """
    Validate a cron expression.

    Returns:
        Tuple of (is_valid, message)
    """
    try:
        from croniter import croniter
    except ImportError:
        # Fallback validation without croniter
        return validate_cron_basic(expression)

    try:
        cron = croniter(expression, datetime.now(timezone.utc))
        # Try to get next occurrence to fully validate
        next_run = cron.get_next(datetime)
        return True, f"Valid. Next run: {next_run.isoformat()}"
    except (ValueError, KeyError) as e:
        return False, f"Invalid: {str(e)}"


def validate_cron_basic(expression: str) -> tuple[bool, str]:
    """Basic cron validation without external dependencies."""
    parts = expression.strip().split()

    if len(parts) != 5:
        return False, f"Invalid: Expected 5 fields, got {len(parts)}"

    field_names = ["minute", "hour", "day", "month", "weekday"]
    field_ranges = [
        (0, 59),   # minute
        (0, 23),   # hour
        (1, 31),   # day
        (1, 12),   # month
        (0, 7),    # weekday (0 and 7 are Sunday)
    ]

    for i, (part, name, (min_val, max_val)) in enumerate(
        zip(parts, field_names, field_ranges)
    ):
        if not validate_cron_field(part, min_val, max_val):
            return False, f"Invalid {name} field: {part}"

    return True, "Valid cron expression"


def validate_cron_field(field: str, min_val: int, max_val: int) -> bool:
    """Validate a single cron field."""
    if field == "*":
        return True

    # Handle */n (step values)
    if field.startswith("*/"):
        try:
            step = int(field[2:])
            return 1 <= step <= max_val
        except ValueError:
            return False

    # Handle ranges and lists
    for part in field.split(","):
        if "-" in part:
            # Range: e.g., 1-5
            try:
                start, end = part.split("-")
                start, end = int(start), int(end)
                if not (min_val <= start <= max_val and min_val <= end <= max_val):
                    return False
            except ValueError:
                return False
        else:
            # Single value
            try:
                val = int(part)
                if not min_val <= val <= max_val:
                    return False
            except ValueError:
                return False

    return True


def explain_cron(expression: str) -> str:
    """Explain a cron expression in human-readable format."""
    parts = expression.strip().split()
    if len(parts) != 5:
        return "Invalid expression"

    minute, hour, day, month, weekday = parts

    explanations = []

    # Minute
    if minute == "*":
        explanations.append("every minute")
    elif minute.startswith("*/"):
        explanations.append(f"every {minute[2:]} minutes")
    elif minute == "0":
        explanations.append("at minute 0")
    else:
        explanations.append(f"at minute {minute}")

    # Hour
    if hour == "*":
        explanations.append("of every hour")
    elif hour.startswith("*/"):
        explanations.append(f"every {hour[2:]} hours")
    else:
        explanations.append(f"at {hour}:00")

    # Day of month
    if day != "*":
        if day.startswith("*/"):
            explanations.append(f"every {day[2:]} days")
        else:
            explanations.append(f"on day {day}")

    # Month
    if month != "*":
        month_names = {
            "1": "January", "2": "February", "3": "March", "4": "April",
            "5": "May", "6": "June", "7": "July", "8": "August",
            "9": "September", "10": "October", "11": "November", "12": "December"
        }
        explanations.append(f"in {month_names.get(month, month)}")

    # Weekday
    if weekday != "*":
        weekday_names = {
            "0": "Sunday", "1": "Monday", "2": "Tuesday", "3": "Wednesday",
            "4": "Thursday", "5": "Friday", "6": "Saturday", "7": "Sunday"
        }
        if "-" in weekday:
            start, end = weekday.split("-")
            explanations.append(
                f"on {weekday_names.get(start, start)} through {weekday_names.get(end, end)}"
            )
        else:
            explanations.append(f"on {weekday_names.get(weekday, weekday)}")

    return " ".join(explanations)


def get_next_runs(expression: str, count: int = 5) -> list[str]:
    """Get the next N run times for a cron expression."""
    try:
        from croniter import croniter
    except ImportError:
        return ["croniter not installed - cannot calculate next runs"]

    try:
        cron = croniter(expression, datetime.now(timezone.utc))
        runs = []
        for _ in range(count):
            next_run = cron.get_next(datetime)
            runs.append(next_run.isoformat())
        return runs
    except Exception as e:
        return [f"Error: {str(e)}"]


def main():
    parser = argparse.ArgumentParser(
        description="Validate cron expressions for Job Scheduler"
    )
    parser.add_argument("expression", help="Cron expression to validate")
    parser.add_argument(
        "--explain", "-e",
        action="store_true",
        help="Explain the cron expression in human-readable format"
    )
    parser.add_argument(
        "--next", "-n",
        type=int,
        default=0,
        metavar="N",
        help="Show next N scheduled run times"
    )

    args = parser.parse_args()

    # Validate
    is_valid, message = validate_cron(args.expression)

    if is_valid:
        print(f"✓ {message}")

        if args.explain:
            print(f"\nExplanation: {explain_cron(args.expression)}")

        if args.next > 0:
            print(f"\nNext {args.next} runs:")
            for i, run in enumerate(get_next_runs(args.expression, args.next), 1):
                print(f"  {i}. {run}")

        sys.exit(0)
    else:
        print(f"✗ {message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
