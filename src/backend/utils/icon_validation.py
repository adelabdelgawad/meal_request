"""
Icon validation utility for lucide-react icon names.

Validates icon identifiers against a static allowlist of lucide-react icons.
"""

import re
from typing import Optional, Set

# Static allowlist of lucide-react icon names (commonly used icons)
# This list can be expanded or loaded from a JSON file via ICON_ALLOWLIST_SOURCE config
LUCIDE_ICON_ALLOWLIST: Set[str] = {
    # Navigation & UI
    "home", "menu", "x", "chevron-down", "chevron-up", "chevron-left", "chevron-right",
    "arrow-left", "arrow-right", "arrow-up", "arrow-down", "more-vertical", "more-horizontal",

    # Settings & Admin
    "settings", "tool", "wrench", "sliders", "toggle-left", "toggle-right",

    # Users & Auth
    "user", "users", "user-plus", "user-minus", "user-check", "user-x",
    "shield", "shield-check", "shield-alert", "lock", "unlock", "key",

    # Files & Documents
    "file", "file-text", "folder", "folder-open", "upload", "download",
    "save", "edit", "trash", "archive",

    # Communication
    "mail", "message-square", "message-circle", "phone", "video",

    # System & Tech
    "cpu", "server", "database", "hard-drive", "terminal", "code",
    "git-branch", "git-commit", "git-pull-request",

    # Actions
    "plus", "minus", "check", "x-circle", "check-circle", "alert-circle",
    "info", "help-circle", "search", "filter", "refresh-cw", "external-link",
    "history", "undo", "redo",

    # Media
    "image", "film", "music", "play", "pause", "stop",

    # Business
    "briefcase", "calendar", "clock", "timer", "dollar-sign", "trending-up", "trending-down",
    "bar-chart", "bar-chart-3", "pie-chart", "activity",

    # Food & Meal
    "utensils", "utensils-crossed", "coffee", "pizza",

    # Documents & Reports
    "clipboard-list", "file-search", "file-text",

    # Location
    "map", "map-pin", "globe", "navigation",

    # Social
    "heart", "star", "bookmark", "share", "send",

    # Misc
    "bell", "tag", "layers", "box", "package", "shopping-cart",
    "copy", "clipboard", "link", "printer", "zap", "eye", "eye-off",
}

# Icon name validation pattern: alphanumeric, hyphen, underscore only
ICON_NAME_PATTERN = re.compile(r'^[A-Za-z0-9_-]{1,64}$')


def is_valid_icon_name(icon: str) -> bool:
    """
    Validate icon name format (pattern check only).

    Args:
        icon: Icon identifier string

    Returns:
        True if icon matches the allowed pattern, False otherwise
    """
    if not icon:
        return False
    return bool(ICON_NAME_PATTERN.match(icon))


def is_icon_in_allowlist(icon: str) -> bool:
    """
    Check if icon exists in the lucide-react allowlist.

    Args:
        icon: Icon identifier string

    Returns:
        True if icon is in allowlist, False otherwise
    """
    if not icon:
        return False
    return icon.lower() in LUCIDE_ICON_ALLOWLIST


def validate_icon(icon: Optional[str], require_allowlist: bool = True) -> tuple[bool, Optional[str]]:
    """
    Validate icon identifier comprehensively.

    Args:
        icon: Icon identifier string (can be None)
        require_allowlist: If True, icon must exist in allowlist

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid
    """
    # None/empty is valid (optional field)
    if not icon:
        return True, None

    # Check pattern
    if not is_valid_icon_name(icon):
        return False, f"Icon '{icon}' contains invalid characters or exceeds 64 characters. Use only letters, numbers, hyphens, and underscores."

    # Check allowlist if required
    if require_allowlist and not is_icon_in_allowlist(icon):
        return False, f"Icon '{icon}' is not in the lucide-react allowlist. Please choose from the available icons."

    return True, None


def get_icon_allowlist() -> Set[str]:
    """
    Get the current icon allowlist.

    Returns:
        Set of allowed icon identifiers
    """
    return LUCIDE_ICON_ALLOWLIST.copy()


def get_icon_allowlist_version() -> str:
    """
    Get the version/hash of the icon allowlist for cache invalidation.

    Returns:
        Version string (e.g., hash of allowlist)
    """
    # Simple version based on allowlist size and a few representative icons
    sample_icons = sorted(list(LUCIDE_ICON_ALLOWLIST))[:5]
    return f"v1-{len(LUCIDE_ICON_ALLOWLIST)}-{''.join(sample_icons[:3])}"
