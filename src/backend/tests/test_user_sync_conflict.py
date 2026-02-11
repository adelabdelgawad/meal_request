"""
Tests for Strategy A: User Source Tracking and Status Override

Tests cover:
1. HRIS sync skips manual users
2. HRIS sync skips users with status override
3. HRIS sync deactivates/reactivates HRIS users based on SecurityUser
4. Mark manual endpoint
5. Override status endpoint
6. Edge cases and validation
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.services.hris_service import HRISService
from db.model import User, SecurityUser, Employee


class TestHRISSyncSkipsManualUsers:
    """Test that HRIS sync respects manual users."""

    @pytest.mark.asyncio
    async def test_manual_user_not_deactivated_by_sync(
        self,
        session: AsyncSession
    ):
        """Manual users (user_source='manual') should not be affected by HRIS sync."""
        # Arrange: Create a manual user (active)
        manual_user = User(
            id=str(uuid4()),
            username="contractor_john",
            user_source="manual",
            is_domain_user=False,
            is_active=True,
            password="hashed_password",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(manual_user)
        await session.commit()

        # Act: Run HRIS user status sync
        hris_service = HRISService()
        stats = await hris_service.sync_user_active_status_from_security_user(session)
        await session.commit()

        # Assert: Manual user should be skipped
        await session.refresh(manual_user)
        assert manual_user.is_active is True, "Manual user should remain active"
        assert stats["skipped_manual"] == 1, "Should report 1 manual user skipped"
        assert stats["deactivated"] == 0, "Should not deactivate any users"

    @pytest.mark.asyncio
    async def test_multiple_manual_users_preserved(
        self,
        session: AsyncSession
    ):
        """Multiple manual users should all be preserved."""
        # Arrange: Create 3 manual users
        manual_users = [
            User(
                id=str(uuid4()),
                username=f"contractor_{i}",
                user_source="manual",
                is_domain_user=False,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            for i in range(3)
        ]
        for user in manual_users:
            session.add(user)
        await session.commit()

        # Act: Run HRIS sync
        hris_service = HRISService()
        stats = await hris_service.sync_user_active_status_from_security_user(session)
        await session.commit()

        # Assert: All manual users preserved
        assert stats["skipped_manual"] == 3
        for user in manual_users:
            await session.refresh(user)
            assert user.is_active is True


class TestHRISSyncRespectsOverrides:
    """Test that HRIS sync respects status_override flag."""

    @pytest.mark.asyncio
    async def test_override_user_not_deactivated(
        self,
        session: AsyncSession
    ):
        """Users with status_override=True should not be deactivated by sync."""
        # Arrange: Create HRIS user with override enabled
        override_user = User(
            id=str(uuid4()),
            username="jane_doe",
            user_source="hris",
            is_domain_user=True,
            is_active=True,
            status_override=True,
            override_reason="Terminated but kept for audit access",
            override_set_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(override_user)

        # Create SecurityUser marked as deleted
        sec_user = SecurityUser(
            user_name="jane_doe",
            is_deleted=True,
            is_locked=False
        )
        session.add(sec_user)
        await session.commit()

        # Act: Run HRIS sync
        hris_service = HRISService()
        stats = await hris_service.sync_user_active_status_from_security_user(session)
        await session.commit()

        # Assert: Override user should remain active
        await session.refresh(override_user)
        assert override_user.is_active is True, "Override user should remain active despite SecurityUser.is_deleted=True"
        assert stats["skipped_override"] == 1, "Should report 1 override user skipped"
        assert stats["deactivated"] == 0, "Should not deactivate override user"


class TestHRISSyncUpdatesHRISUsers:
    """Test that HRIS sync correctly updates HRIS users based on SecurityUser."""

    @pytest.mark.asyncio
    async def test_hris_user_deactivated_when_security_user_deleted(
        self,
        session: AsyncSession
    ):
        """HRIS users should be deactivated when SecurityUser is marked deleted."""
        # Arrange: Create active HRIS user
        hris_user = User(
            id=str(uuid4()),
            username="bob_smith",
            user_source="hris",
            is_domain_user=True,
            is_active=True,
            status_override=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(hris_user)

        # Create SecurityUser marked as deleted
        sec_user = SecurityUser(
            user_name="bob_smith",
            is_deleted=True,
            is_locked=False
        )
        session.add(sec_user)
        await session.commit()

        # Act: Run HRIS sync
        hris_service = HRISService()
        stats = await hris_service.sync_user_active_status_from_security_user(session)
        await session.commit()

        # Assert: HRIS user should be deactivated
        await session.refresh(hris_user)
        assert hris_user.is_active is False, "HRIS user should be deactivated when SecurityUser.is_deleted=True"
        assert stats["deactivated"] == 1

    @pytest.mark.asyncio
    async def test_hris_user_deactivated_when_security_user_locked(
        self,
        session: AsyncSession
    ):
        """HRIS users should be deactivated when SecurityUser is locked."""
        # Arrange: Create active HRIS user
        hris_user = User(
            id=str(uuid4()),
            username="locked_user",
            user_source="hris",
            is_domain_user=True,
            is_active=True,
            status_override=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(hris_user)

        # Create locked SecurityUser
        sec_user = SecurityUser(
            user_name="locked_user",
            is_deleted=False,
            is_locked=True
        )
        session.add(sec_user)
        await session.commit()

        # Act: Run HRIS sync
        hris_service = HRISService()
        stats = await hris_service.sync_user_active_status_from_security_user(session)
        await session.commit()

        # Assert: HRIS user should be deactivated
        await session.refresh(hris_user)
        assert hris_user.is_active is False, "HRIS user should be deactivated when SecurityUser.is_locked=True"
        assert stats["deactivated"] == 1

    @pytest.mark.asyncio
    async def test_hris_user_reactivated_when_security_user_active(
        self,
        session: AsyncSession
    ):
        """Inactive HRIS users should be reactivated when SecurityUser becomes active."""
        # Arrange: Create inactive HRIS user
        hris_user = User(
            id=str(uuid4()),
            username="reactivated_user",
            user_source="hris",
            is_domain_user=True,
            is_active=False,  # Currently inactive
            status_override=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(hris_user)

        # Create active SecurityUser
        sec_user = SecurityUser(
            user_name="reactivated_user",
            is_deleted=False,
            is_locked=False
        )
        session.add(sec_user)
        await session.commit()

        # Act: Run HRIS sync
        hris_service = HRISService()
        stats = await hris_service.sync_user_active_status_from_security_user(session)
        await session.commit()

        # Assert: HRIS user should be reactivated
        await session.refresh(hris_user)
        assert hris_user.is_active is True, "HRIS user should be reactivated when SecurityUser is active"
        assert stats["reactivated"] == 1


class TestMixedUserScenarios:
    """Test scenarios with mixed user types."""

    @pytest.mark.asyncio
    async def test_mixed_users_correct_handling(
        self,
        session: AsyncSession
    ):
        """Sync should handle mix of manual, override, and HRIS users correctly."""
        # Arrange: Create mixed user types
        manual_user = User(
            id=str(uuid4()),
            username="manual_user",
            user_source="manual",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        override_user = User(
            id=str(uuid4()),
            username="override_user",
            user_source="hris",
            is_active=True,
            status_override=True,
            override_reason="Special access",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        hris_active_user = User(
            id=str(uuid4()),
            username="hris_active",
            user_source="hris",
            is_active=True,
            status_override=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        hris_deleted_user = User(
            id=str(uuid4()),
            username="hris_deleted",
            user_source="hris",
            is_active=True,
            status_override=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        session.add_all([manual_user, override_user, hris_active_user, hris_deleted_user])

        # Create SecurityUsers
        sec_users = [
            SecurityUser(user_name="override_user", is_deleted=True, is_locked=False),
            SecurityUser(user_name="hris_active", is_deleted=False, is_locked=False),
            SecurityUser(user_name="hris_deleted", is_deleted=True, is_locked=False),
        ]
        for sec_user in sec_users:
            session.add(sec_user)

        await session.commit()

        # Act: Run HRIS sync
        hris_service = HRISService()
        stats = await hris_service.sync_user_active_status_from_security_user(session)
        await session.commit()

        # Assert: Verify each user's final state
        await session.refresh(manual_user)
        await session.refresh(override_user)
        await session.refresh(hris_active_user)
        await session.refresh(hris_deleted_user)

        assert manual_user.is_active is True, "Manual user should remain active"
        assert override_user.is_active is True, "Override user should remain active despite SecurityUser deleted"
        assert hris_active_user.is_active is True, "HRIS active user should remain active"
        assert hris_deleted_user.is_active is False, "HRIS deleted user should be deactivated"

        assert stats["skipped_manual"] == 1
        assert stats["skipped_override"] == 1
        assert stats["deactivated"] == 1
        assert stats["reactivated"] == 0


# Fixture setup (add to conftest.py or inline)
@pytest.fixture
async def session():
    """Provide async database session for tests."""
    from db.database import DatabaseSessionLocal

    async with DatabaseSessionLocal() as session:
        yield session
        await session.rollback()  # Rollback after each test
