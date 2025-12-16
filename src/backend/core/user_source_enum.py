"""
User Source Enum with Localized Metadata

Provides bilingual (English/Arabic) labels and descriptions for user source types.
This allows the frontend to display localized labels while using consistent codes internally.
"""

from enum import Enum
from typing import Dict, List
from pydantic import Field

# Import CamelModel for consistent camelCase JSON serialization
from api.schemas._base import CamelModel


class UserSourceCode(str, Enum):
    """Technical codes for user sources (stored in database)."""

    HRIS = "hris"
    MANUAL = "manual"


class UserSourceMetadata(CamelModel):
    """Localized metadata for a user source type."""

    code: str = Field(
        description="Technical identifier used in database and business logic"
    )
    name_en: str = Field(description="English display name")
    name_ar: str = Field(description="Arabic display name")
    description_en: str = Field(description="English description for UI tooltips/help")
    description_ar: str = Field(description="Arabic description for UI tooltips/help")
    icon: str = Field(
        description="Icon identifier for UI (e.g., 'database', 'user-edit')"
    )
    color: str = Field(
        description="Color code for UI badges (e.g., 'blue', 'green', 'gray')"
    )
    can_override: bool = Field(
        description="Whether users of this source can have status overrides"
    )


# Centralized user source definitions with bilingual metadata
USER_SOURCE_DEFINITIONS: Dict[str, UserSourceMetadata] = {
    UserSourceCode.HRIS: UserSourceMetadata(
        code="hris",
        name_en="HRIS User",
        name_ar="مستخدم HRIS",
        description_en="User synchronized from the HRIS system. Account status is controlled by HRIS data unless manually overridden.",
        description_ar="مستخدم متزامن من نظام الموارد البشرية. حالة الحساب يتحكم فيها بيانات الموارد البشرية ما لم يتم تجاوزها يدويًا.",
        icon="database",
        color="blue",
        can_override=True,
    ),
    UserSourceCode.MANUAL: UserSourceMetadata(
        code="manual",
        name_en="Manual User",
        name_ar="مستخدم يدوي",
        description_en="User created manually by an administrator. Not linked to HRIS. Fully controlled within the application.",
        description_ar="مستخدم تم إنشاؤه يدويًا بواسطة المسؤول. غير مرتبط بنظام الموارد البشرية. يتم التحكم فيه بالكامل داخل التطبيق.",
        icon="user-edit",
        color="green",
        can_override=False,
    ),
}


def get_user_source_metadata(code: str) -> UserSourceMetadata:
    """
    Get metadata for a specific user source code.

    Args:
        code: User source code ('hris' or 'manual')

    Returns:
        UserSourceMetadata object with localized labels

    Raises:
        KeyError: If code is not recognized
    """
    return USER_SOURCE_DEFINITIONS[code]


def get_all_user_sources() -> List[UserSourceMetadata]:
    """
    Get metadata for all available user sources.

    Returns:
        List of UserSourceMetadata objects in a consistent order
    """
    return [
        USER_SOURCE_DEFINITIONS[UserSourceCode.HRIS],
        USER_SOURCE_DEFINITIONS[UserSourceCode.MANUAL],
    ]


def get_localized_name(code: str, locale: str = "en") -> str:
    """
    Get localized name for a user source.

    Args:
        code: User source code
        locale: Language code ('en' or 'ar')

    Returns:
        Localized name string
    """
    metadata = get_user_source_metadata(code)
    return metadata.name_ar if locale == "ar" else metadata.name_en


def get_localized_description(code: str, locale: str = "en") -> str:
    """
    Get localized description for a user source.

    Args:
        code: User source code
        locale: Language code ('en' or 'ar')

    Returns:
        Localized description string
    """
    metadata = get_user_source_metadata(code)
    return metadata.description_ar if locale == "ar" else metadata.description_en
