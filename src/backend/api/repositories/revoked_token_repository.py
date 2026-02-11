"""RevokedToken Repository - Data access layer for RevokedToken entity."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError
from db.model import RevokedToken
from .base import BaseRepository


class RevokedTokenRepository(BaseRepository[RevokedToken]):
    """Repository for RevokedToken entity."""

        super().__init__(session)

    async def create(self, token: RevokedToken) -> RevokedToken:
        try:
            self.session.add(token)
            await self.session.flush()
            return token
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to create revoked token: {str(e)}")

    async def get_by_id(self, token_id: int) -> Optional[RevokedToken]:
        result = await self.session.execute(
            select(RevokedToken).where(RevokedToken.id == token_id)
        )
        return result.scalar_one_or_none()

    async def get_by_jti(self, jti: str) -> Optional[RevokedToken]:
        """Check if a token JTI is revoked."""
        result = await self.session.execute(
            select(RevokedToken).where(RevokedToken.jti == jti)
        )
        return result.scalar_one_or_none()

    async def is_revoked(self, jti: str) -> bool:
        """Check if a token is revoked."""
        token = await self.get_by_jti(session, jti)
        return token is not None

    async def delete(self, token_id: int) -> None:
        token = await self.get_by_id(token_id)
        if token:
            await self.session.delete(token)
            await self.session.flush()
