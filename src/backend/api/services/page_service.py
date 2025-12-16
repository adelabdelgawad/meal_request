"""Page Service - Business logic for page management."""

from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.page_repository import PageRepository
from core.exceptions import ConflictError, NotFoundError, ValidationError
from db.models import Page
from utils.icon_validation import validate_icon


class PageService:
    """Service for page management operations."""

    def __init__(self):
        """Initialize service."""
        self._repo = PageRepository()

    async def create_page(
        self,
        session: AsyncSession,
        name_en: str,
        name_ar: str,
        description_en: Optional[str] = None,
        description_ar: Optional[str] = None,
        path: Optional[str] = None,
        icon: Optional[str] = None,
        nav_type: Optional[str] = None,
        order: int = 100,
        is_menu_group: bool = False,
        show_in_nav: bool = True,
        open_in_new_tab: bool = False,
        parent_id: Optional[int] = None,
        key: Optional[str] = None,
    ) -> Page:
        """Create a new page with bilingual support and navigation fields."""
        # Check if page exists with same English name
        existing = await self._repo.get_by_name_en(session, name_en)
        if existing:
            raise ConflictError(entity="Page", field="name_en", value=name_en)

        # Validate icon if provided
        if icon:
            is_valid, error_msg = validate_icon(icon, require_allowlist=True)
            if not is_valid:
                raise ValidationError(message=error_msg, field="icon")

        page = Page(
            name_en=name_en,
            name_ar=name_ar,
            description_en=description_en,
            description_ar=description_ar,
            path=path,
            icon=icon,
            nav_type=nav_type,
            order=order,
            is_menu_group=is_menu_group,
            show_in_nav=show_in_nav,
            open_in_new_tab=open_in_new_tab,
            parent_id=parent_id,
            key=key,
        )
        return await self._repo.create(session, page)

    async def get_page(self, session: AsyncSession, page_id: int) -> Page:
        """Get a page by ID."""
        page = await self._repo.get_by_id(session, page_id)
        if not page:
            raise NotFoundError(entity="Page", identifier=page_id)
        return page

    async def get_page_by_name(self, session: AsyncSession, name: str) -> Page:
        """Get a page by name."""
        page = await self._repo.get_by_name(session, name)
        if not page:
            raise NotFoundError(entity="Page", identifier=name)
        return page

    async def list_pages(
        self, session: AsyncSession, page: int = 1, per_page: int = 25
    ) -> Tuple[List[Page], int]:
        """List pages with pagination."""
        return await self._repo.list(session, page=page, per_page=per_page)

    async def update_page(
        self,
        session: AsyncSession,
        page_id: int,
        name_en: Optional[str] = None,
        name_ar: Optional[str] = None,
        description_en: Optional[str] = None,
        description_ar: Optional[str] = None,
        path: Optional[str] = None,
        icon: Optional[str] = None,
        nav_type: Optional[str] = None,
        order: Optional[int] = None,
        is_menu_group: Optional[bool] = None,
        show_in_nav: Optional[bool] = None,
        open_in_new_tab: Optional[bool] = None,
    ) -> Page:
        """Update a page with bilingual support and navigation fields."""
        update_data = {}

        # If name_en is being updated, check for conflicts
        if name_en is not None:
            existing = await self._repo.get_by_name_en(session, name_en)
            if existing and existing.id != page_id:
                raise ConflictError(entity="Page", field="name_en", value=name_en)
            update_data["name_en"] = name_en

        if name_ar is not None:
            update_data["name_ar"] = name_ar
        if description_en is not None:
            update_data["description_en"] = description_en
        if description_ar is not None:
            update_data["description_ar"] = description_ar

        # Navigation fields
        if path is not None:
            update_data["path"] = path
        if nav_type is not None:
            update_data["nav_type"] = nav_type
        if order is not None:
            update_data["order"] = order
        if is_menu_group is not None:
            update_data["is_menu_group"] = is_menu_group
        if show_in_nav is not None:
            update_data["show_in_nav"] = show_in_nav
        if open_in_new_tab is not None:
            update_data["open_in_new_tab"] = open_in_new_tab

        # Validate and set icon if provided
        if icon is not None:
            is_valid, error_msg = validate_icon(icon, require_allowlist=True)
            if not is_valid:
                raise ValidationError(message=error_msg, field="icon")
            update_data["icon"] = icon

        return await self._repo.update(session, page_id, update_data)

    async def delete_page(self, session: AsyncSession, page_id: int) -> None:
        """Delete a page."""
        await self._repo.delete(session, page_id)

    async def get_all_pages(self, session: AsyncSession) -> Optional[List[Page]]:
        """
        Get all available pages for super admin.

        Args:
            session: Database session

        Returns:
            List of all pages, or None if none found
        """
        return await self._repo.get_all(session)

    async def get_pages_by_account(
        self, session: AsyncSession, account_id: int
    ) -> Optional[List[Page]]:
        """
        Get pages accessible by a user based on their role permissions.

        Args:
            session: Database session
            account_id: User ID (UUID)

        Returns:
            List of pages accessible to the user, or None if none found
        """
        return await self._repo.get_pages_by_account(session, account_id)
