"""Page Repository."""

from typing import List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from core.exceptions import DatabaseError, NotFoundError
from db.model import Page, PagePermission, Role, User, RolePermission
from .base import BaseRepository


class PageRepository(BaseRepository[Page]):
    """Repository for Page entity."""

    model = Page

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create(self, page: Page) -> Page:
        """
        Create a page or update if it already exists (upsert logic).
        If a page with the same name_en exists, it will be updated instead of raising an error.
        """
        # Check if page with same name_en already exists
        existing = await self.get_by_name_en(page.name_en)
        if existing:
            # Update existing page
            for key, value in page.__dict__.items():
                if not key.startswith("_") and key != "id" and hasattr(existing, key):
                    setattr(existing, key, value)
            await self.session.flush()
            return existing

        # Create new page
        try:
            self.session.add(page)
            await self.session.flush()
            return page
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to create page: {str(e)}")

    async def get_by_name(
        self, name: str, locale: Optional[str] = None
    ) -> Optional[Page]:
        """
        Get page by name. If locale is specified, search in the corresponding language field.
        Otherwise, search in both name_en and name_ar.
        """
        if locale == "ar":
            result = await self.session.execute(
                select(Page).where(Page.name_ar == name)
            )
        elif locale == "en":
            result = await self.session.execute(
                select(Page).where(Page.name_en == name)
            )
        else:
            # Search in both fields
            result = await self.session.execute(
                select(Page).where((Page.name_en == name) | (Page.name_ar == name))
            )
        return result.scalar_one_or_none()

    async def get_by_name_en(self, name_en: str) -> Optional[Page]:
        """Get page by English name."""
        result = await self.session.execute(select(Page).where(Page.name_en == name_en))
        return result.scalar_one_or_none()

    async def get_by_name_ar(self, name_ar: str) -> Optional[Page]:
        """Get page by Arabic name."""
        result = await self.session.execute(select(Page).where(Page.name_ar == name_ar))
        return result.scalar_one_or_none()

    async def list(self, page: int = 1, per_page: int = 25) -> Tuple[List[Page], int]:
        from core.pagination import calculate_offset

        # Optimized count query

        count_query = select(func.count()).select_from((select(Page)).subquery())

        count_result = await self.session.execute(count_query)

        total = count_result.scalar() or 0

        offset = calculate_offset(page, per_page)
        result = await self.session.execute(select(Page).offset(offset).limit(per_page))
        return result.scalars().all(), total

    async def update(self, page_id: int, page_data: dict) -> Page:
        page = await self.get_by_id(page_id)
        if not page:
            raise NotFoundError(entity="Page", identifier=page_id)

        try:
            for key, value in page_data.items():
                if value is not None and hasattr(page, key):
                    setattr(page, key, value)

            await self.session.flush()
            return page
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to update page: {str(e)}")

    # Specialized CRUD compatibility methods
    async def get_pages_by_user(self, user_id: UUID) -> Optional[List[Page]]:
        """Get pages accessible to a specific user based on their roles."""
        try:
            stmt = (
                select(Page)
                .distinct()
                .join(PagePermission, Page.page_permissions)
                .join(Role, PagePermission.role)
                .join(RolePermission, Role.role_permissions)
                .join(User, RolePermission.user)
                .where(User.id == user_id)
            )

            result = await self.session.execute(stmt)
            pages = result.scalars().all()

            return list(set(pages)) if pages else []
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve pages for user: {str(e)}")

    async def get_all(self) -> Optional[List[Page]]:
        """Get all pages that should be shown in navigation."""
        try:
            stmt = select(Page).where(Page.show_in_nav).order_by(Page.order, Page.id)
            result = await self.session.execute(stmt)
            pages = result.scalars().all()
            return pages if pages else None
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve all pages: {str(e)}")

    async def get_pages_by_account(self, account_id: int) -> Optional[List[Page]]:
        """
        Get pages accessible to a user based on their roles, filtered by show_in_nav.

        Args:
            account_id: User ID (UUID)

        Returns:
            List of pages accessible to the user that should be shown in navigation
        """
        try:
            # Get the user and their pages through roles
            stmt = (
                select(Page)
                .distinct()
                .join(PagePermission, Page.page_permissions)
                .join(Role, PagePermission.role)
                .join(RolePermission, Role.role_permissions)
                .join(User, RolePermission.user)
                .where(User.id == account_id)
                .where(Page.show_in_nav)
                .order_by(Page.order, Page.id)
            )

            result = await self.session.execute(stmt)
            pages = result.scalars().all()

            return pages if pages else None
        except Exception as e:
            raise DatabaseError(
                f"Failed to retrieve pages for user {account_id}: {str(e)}"
            )

    # Navigation-specific methods
    async def get_by_key(self, key: str) -> Optional[Page]:
        """Get page by unique key (for idempotent seeds)."""
        result = await self.session.execute(select(Page).where(Page.key == key))
        return result.scalar_one_or_none()

    async def upsert_by_key(self, page: Page) -> Page:
        """
        Upsert page by key. If page with key exists, update it; otherwise create new.

        Args:
            page: Page object with key set

        Returns:
            Created or updated Page object
        """
        if not page.key:
            raise DatabaseError("Page key is required for upsert operation")

        existing = await self.get_by_key(page.key)
        if existing:
            # Update existing page (preserve certain fields if needed)
            for key, value in page.__dict__.items():
                if not key.startswith("_") and key != "id" and hasattr(existing, key):
                    setattr(existing, key, value)
            await self.session.flush()
            return existing

        # Create new page
        try:
            self.session.add(page)
            await self.session.flush()
            return page
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to upsert page: {str(e)}")

    async def get_navigation_pages(
        self, nav_type: Optional[str] = None, show_in_nav_only: bool = True
    ) -> List[Page]:
        """
        Get pages for navigation tree building.

        Args:
            nav_type: Filter by nav_type (e.g., 'primary', 'sidebar')
            show_in_nav_only: Only include pages with show_in_nav=True

        Returns:
            List of Page objects suitable for navigation
        """
        stmt = select(Page)

        if show_in_nav_only:
            stmt = stmt.where(Page.show_in_nav)

        if nav_type:
            stmt = stmt.where(Page.nav_type == nav_type)

        # Order by parent_id (nulls first) and then by order
        stmt = stmt.order_by(Page.parent_id.is_(None).desc(), Page.order)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_children(self, parent_id: int) -> List[Page]:
        """Get immediate children of a parent page."""
        result = await self.session.execute(
            select(Page).where(Page.parent_id == parent_id).order_by(Page.order)
        )
        return list(result.scalars().all())

    async def get_children(self, parent_id: int) -> List[Page]:
        """Get immediate children of a parent page."""
        result = await session.execute(
            select(Page).where(Page.parent_id == parent_id).order_by(Page.order)
        )
        return list(result.scalars().all())
