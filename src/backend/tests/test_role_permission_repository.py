"""Tests for RolePermissionRepository."""

import pytest
from uuid import uuid4

from api.repositories.role_permission_repository import RolePermissionRepository
from core.exceptions import NotFoundError
from db.models import Role, User


@pytest.fixture
def repo():
    """Create repository instance."""
    return RolePermissionRepository()


@pytest.fixture
async def sample_user(session):
    """Create a sample user for testing."""
    user = User(
        id=str(uuid4()),
        username="testuser",
        email="test@example.com",
        is_domain_user=True,
    )
    session.add(user)
    await session.flush()
    return user


@pytest.fixture
async def sample_role(session):
    """Create a sample role for testing."""
    role = Role(
        id=str(uuid4()),
        name_en="Test Role",
        name_ar="دور اختبار",
    )
    session.add(role)
    await session.flush()
    return role


class TestRolePermissionRepository:
    """Test RolePermissionRepository."""

    async def test_assign_role_to_user(self, repo, session, sample_user, sample_role):
        """Test assigning a role to a user."""
        permission = await repo.assign_role_to_user(
            session,
            user_id=sample_user.id,
            role_id=sample_role.id,
        )

        assert permission is not None
        assert permission.user_id == str(sample_user.id)
        assert permission.role_id == str(sample_role.id)

    async def test_assign_role_twice_returns_existing(
        self, repo, session, sample_user, sample_role
    ):
        """Test that assigning the same role twice returns existing record."""
        permission1 = await repo.assign_role_to_user(
            session,
            user_id=sample_user.id,
            role_id=sample_role.id,
        )

        permission2 = await repo.assign_role_to_user(
            session,
            user_id=sample_user.id,
            role_id=sample_role.id,
        )

        assert permission1.id == permission2.id

    async def test_get_roles_by_user(self, repo, session, sample_user, sample_role):
        """Test getting all roles for a user."""
        await repo.assign_role_to_user(
            session,
            user_id=sample_user.id,
            role_id=sample_role.id,
        )

        roles = await repo.get_roles_by_user(session, sample_user.id)

        assert len(roles) == 1
        assert roles[0].id == sample_role.id

    async def test_get_users_by_role(self, repo, session, sample_user, sample_role):
        """Test getting all users for a role."""
        await repo.assign_role_to_user(
            session,
            user_id=sample_user.id,
            role_id=sample_role.id,
        )

        users = await repo.get_users_by_role(session, sample_role.id)

        assert len(users) == 1
        assert users[0].id == sample_user.id

    async def test_revoke_role_from_user(self, repo, session, sample_user, sample_role):
        """Test revoking a role from a user."""
        await repo.assign_role_to_user(
            session,
            user_id=sample_user.id,
            role_id=sample_role.id,
        )

        await repo.revoke_role_from_user(
            session,
            user_id=sample_user.id,
            role_id=sample_role.id,
        )

        roles = await repo.get_roles_by_user(session, sample_user.id)
        assert len(roles) == 0

    async def test_revoke_nonexistent_role_raises_error(
        self, repo, session, sample_user, sample_role
    ):
        """Test that revoking a non-existent role raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await repo.revoke_role_from_user(
                session,
                user_id=sample_user.id,
                role_id=sample_role.id,
            )

    async def test_assign_multiple_roles_to_user(
        self, repo, session, sample_user
    ):
        """Test assigning multiple roles to a user."""
        # Create multiple roles
        role1 = Role(id=str(uuid4()), name_en="Role 1", name_ar="دور 1")
        role2 = Role(id=str(uuid4()), name_en="Role 2", name_ar="دور 2")
        session.add(role1)
        session.add(role2)
        await session.flush()

        # Assign roles
        permissions = await repo.assign_roles_to_user(
            session,
            user_id=sample_user.id,
            role_ids=[role1.id, role2.id],
        )

        assert len(permissions) == 2

        # Verify roles were assigned
        roles = await repo.get_roles_by_user(session, sample_user.id)
        assert len(roles) == 2

    async def test_assign_roles_replaces_existing(
        self, repo, session, sample_user
    ):
        """Test that assign_roles_to_user replaces existing assignments."""
        # Create roles
        role1 = Role(id=str(uuid4()), name_en="Role 1", name_ar="دور 1")
        role2 = Role(id=str(uuid4()), name_en="Role 2", name_ar="دور 2")
        role3 = Role(id=str(uuid4()), name_en="Role 3", name_ar="دور 3")
        session.add_all([role1, role2, role3])
        await session.flush()

        # Assign initial roles
        await repo.assign_roles_to_user(
            session,
            user_id=sample_user.id,
            role_ids=[role1.id, role2.id],
        )

        # Replace with new roles
        await repo.assign_roles_to_user(
            session,
            user_id=sample_user.id,
            role_ids=[role3.id],
        )

        # Verify only role3 is assigned
        roles = await repo.get_roles_by_user(session, sample_user.id)
        assert len(roles) == 1
        assert roles[0].id == role3.id

    async def test_has_role(self, repo, session, sample_user, sample_role):
        """Test checking if a user has a specific role."""
        # User doesn't have role initially
        has_role = await repo.has_role(session, sample_user.id, sample_role.id)
        assert has_role is False

        # Assign role
        await repo.assign_role_to_user(
            session,
            user_id=sample_user.id,
            role_id=sample_role.id,
        )

        # User now has role
        has_role = await repo.has_role(session, sample_user.id, sample_role.id)
        assert has_role is True

    async def test_count_users_in_role(self, repo, session, sample_role):
        """Test counting users in a role."""
        # Create multiple users
        user1 = User(id=str(uuid4()), username="user1", is_domain_user=True)
        user2 = User(id=str(uuid4()), username="user2", is_domain_user=True)
        session.add_all([user1, user2])
        await session.flush()

        # Assign role to users
        await repo.assign_role_to_user(session, user1.id, sample_role.id)
        await repo.assign_role_to_user(session, user2.id, sample_role.id)

        # Count users
        count = await repo.count_users_in_role(session, sample_role.id)
        assert count == 2

    async def test_count_roles_for_user(self, repo, session, sample_user):
        """Test counting roles for a user."""
        # Create multiple roles
        role1 = Role(id=str(uuid4()), name_en="Role 1", name_ar="دور 1")
        role2 = Role(id=str(uuid4()), name_en="Role 2", name_ar="دور 2")
        session.add_all([role1, role2])
        await session.flush()

        # Assign roles to user
        await repo.assign_role_to_user(session, sample_user.id, role1.id)
        await repo.assign_role_to_user(session, sample_user.id, role2.id)

        # Count roles
        count = await repo.count_roles_for_user(session, sample_user.id)
        assert count == 2
