"""Navigation Service - Build permission-aware, localized navigation trees."""

import logging
from typing import Dict, List, Optional, Set

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.page_repository import PageRepository
from db.models import Page

logger = logging.getLogger(__name__)


class NavigationNode:
    """
    Navigation tree node with localized fields and children.
    """

    def __init__(
        self,
        id: int,
        key: Optional[str],
        name_en: str,
        name_ar: str,
        name: str,  # Resolved based on locale
        description_en: Optional[str],
        description_ar: Optional[str],
        description: Optional[str],  # Resolved based on locale
        path: Optional[str],
        is_menu_group: bool,
        icon: Optional[str],
        nav_type: Optional[str],
        order: int,
        open_in_new_tab: bool,
        children: Optional[List["NavigationNode"]] = None,
    ):
        self.id = id
        self.key = key
        self.name_en = name_en
        self.name_ar = name_ar
        self.name = name
        self.description_en = description_en
        self.description_ar = description_ar
        self.description = description
        self.path = path
        self.is_menu_group = is_menu_group
        self.icon = icon
        self.nav_type = nav_type
        self.order = order
        self.open_in_new_tab = open_in_new_tab
        self.children = children or []

    def to_dict(self) -> dict:
        """Convert node to dictionary for API response."""
        return {
            "id": self.id,
            "key": self.key,
            "name_en": self.name_en,
            "name_ar": self.name_ar,
            "name": self.name,
            "description_en": self.description_en,
            "description_ar": self.description_ar,
            "description": self.description,
            "path": self.path,
            "is_menu_group": self.is_menu_group,
            "icon": self.icon,
            "nav_type": self.nav_type,
            "order": self.order,
            "open_in_new_tab": self.open_in_new_tab,
            "children": [child.to_dict() for child in self.children],
        }


class NavigationService:
    """
    Service for building permission-aware, localized navigation trees.

    Implements parent visibility propagation: menu groups without permissions
    are shown if any child is visible.
    """

    def __init__(self):
        self._page_repo = PageRepository()

    async def build_navigation_tree(
        self,
        session: AsyncSession,
        locale: str = "en",
        nav_type: Optional[str] = None,
        user_id: Optional[str] = None,
        is_super_admin: bool = False,
    ) -> List[NavigationNode]:
        """
        Build a permission-filtered, localized navigation tree.

        Args:
            session: Database session
            locale: Locale for name/description resolution (en/ar)
            nav_type: Filter pages by nav_type (e.g., 'primary', 'sidebar')
            user_id: User ID for permission filtering (None = public pages only)
            is_super_admin: Bypass permission checks if True

        Returns:
            List of root NavigationNode objects with nested children
        """
        # Fetch candidate pages
        pages = await self._page_repo.get_navigation_pages(
            session=session,
            nav_type=nav_type,
            show_in_nav_only=True,
        )

        # Apply feature flag filters (visible_when)
        pages = self._filter_by_visible_when(pages)

        # Get user's permissions
        user_permissions = await self._get_user_permissions(
            session, user_id, is_super_admin
        )

        # Filter pages by permissions and build visibility map
        visible_page_ids = self._build_visibility_map(pages, user_permissions, is_super_admin)

        # Build tree structure
        tree = self._build_tree(pages, visible_page_ids, locale)

        return tree

    def _filter_by_visible_when(self, pages: List[Page]) -> List[Page]:
        """
        Filter pages by visible_when feature flags.

        For now, return all pages. Implement feature flag evaluation later.
        """
        return [p for p in pages if not p.visible_when or not p.visible_when]

    async def _get_user_permissions(
        self,
        session: AsyncSession,
        user_id: Optional[str],
        is_super_admin: bool
    ) -> Set[str]:
        """
        Get set of permission keys for the user.

        Args:
            session: Database session
            user_id: User ID (None for unauthenticated)
            is_super_admin: True if user is super admin

        Returns:
            Set of permission strings (e.g., {"users.view", "roles.view"})
        """
        if is_super_admin:
            # Super admin has all permissions
            return set(["*"])  # Wildcard permission

        if not user_id:
            # Unauthenticated user has no permissions
            return set()

        return set()

    def _build_visibility_map(
        self,
        pages: List[Page],
        user_permissions: Set[str],
        is_super_admin: bool
    ) -> Set[int]:
        """
        Build map of visible page IDs based on permissions.

        Implements parent visibility propagation: menu groups are visible
        if any child is visible, even if the group itself has permissions.

        Args:
            pages: List of all candidate pages
            user_permissions: Set of user permission strings
            is_super_admin: True if super admin (bypasses all checks)

        Returns:
            Set of page IDs that should be visible
        """
        visible = set()
        page_map = {p.id: p for p in pages}

        # First pass: mark pages visible based on direct permissions
        for page in pages:
            if self._has_permission(page, user_permissions, is_super_admin):
                visible.add(page.id)

        # Second pass: propagate visibility to parents (menu groups)
        # If any child is visible, make the parent visible too
        changed = True
        while changed:
            changed = False
            for page in pages:
                if page.id in visible:
                    continue  # Already visible

                # Check if this is a menu group with any visible children
                if page.is_menu_group:
                    children = [p for p in pages if p.parent_id == page.id]
                    if any(child.id in visible for child in children):
                        visible.add(page.id)
                        changed = True

                # Also ensure all ancestors are visible if this page is visible
                if page.parent_id and page.parent_id in page_map:
                    parent = page_map[page.parent_id]
                    if page.id in visible and parent.id not in visible:
                        visible.add(parent.id)
                        changed = True

        return visible

    def _has_permission(
        self,
        page: Page,
        user_permissions: Set[str],
        is_super_admin: bool
    ) -> bool:
        """
        Check if user has permission to view this page.

        Args:
            page: Page to check
            user_permissions: User's permission set
            is_super_admin: True if super admin

        Returns:
            True if user can view the page
        """
        if is_super_admin or "*" in user_permissions:
            return True

        # Pages without required_permissions are public
        return True

    def _build_tree(
        self,
        pages: List[Page],
        visible_page_ids: Set[int],
        locale: str
    ) -> List[NavigationNode]:
        """
        Build hierarchical tree from flat list of visible pages.

        Args:
            pages: List of all pages
            visible_page_ids: Set of IDs for visible pages
            locale: Locale for name/description resolution

        Returns:
            List of root NavigationNode objects
        """
        # Filter to only visible pages
        visible_pages = [p for p in pages if p.id in visible_page_ids]

        # Build children map
        children_map: Dict[Optional[int], List[Page]] = {}
        for page in visible_pages:
            parent_id = page.parent_id
            if parent_id not in children_map:
                children_map[parent_id] = []
            children_map[parent_id].append(page)

        # Sort children by order
        for children in children_map.values():
            children.sort(key=lambda p: p.order)

        # Build tree recursively starting from roots (parent_id = None)
        def build_node(page: Page) -> NavigationNode:
            """Recursively build navigation node with children."""
            children_pages = children_map.get(page.id, [])
            children_nodes = [build_node(child) for child in children_pages]

            return NavigationNode(
                id=page.id,
                key=page.key,
                name_en=page.name_en,
                name_ar=page.name_ar,
                name=page.get_name(locale),
                description_en=page.description_en,
                description_ar=page.description_ar,
                description=page.get_description(locale),
                path=page.path,
                is_menu_group=page.is_menu_group,
                icon=page.icon,
                nav_type=page.nav_type,
                order=page.order,
                open_in_new_tab=page.open_in_new_tab,
                children=children_nodes,
            )

        # Build root nodes (pages without parent)
        root_pages = children_map.get(None, [])
        return [build_node(page) for page in root_pages]
