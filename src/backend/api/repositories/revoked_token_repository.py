"""RevokedToken Repository - Data access layer for RevokedToken entity."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError
from db.models import RevokedToken


class RevokedTokenRepository:
    """Repository for RevokedToken entity."""

    def __init__(self):
        pass

    async def create(self, session: AsyncSession, token: RevokedToken) -> RevokedToken:
        try:
            session.add(token)
            await session.flush()
            return token
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to create revoked token: {str(e)}")

    async def get_by_id(self, session: AsyncSession, token_id: int) -> Optional[RevokedToken]:
        result = await session.execute(
            select(RevokedToken).where(RevokedToken.id == token_id)
        )
        return result.scalar_one_or_none()

    async def get_by_jti(self, session: AsyncSession, jti: str) -> Optional[RevokedToken]:
        """Check if a token JTI is revoked."""
        result = await session.execute(
            select(RevokedToken).where(RevokedToken.jti == jti)
        )
        return result.scalar_one_or_none()

    async def is_revoked(self, session: AsyncSession, jti: str) -> bool:
        """Check if a token is revoked."""
        token = await self.get_by_jti(session, jti)
        return token is not None

    async def delete(self, session: AsyncSession, token_id: int) -> None:
        token = await self.get_by_id(session, token_id)
        if token:
            await session.delete(token)
            await session.flush()
