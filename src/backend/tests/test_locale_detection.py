"""Comprehensive tests for locale detection and integration."""

import pytest
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch

from api.deps import get_locale, parse_accept_language
from db.models import Base, User
from settings import settings


# Test database URL (in-memory SQLite for testing)
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_db():
    """Create test database and tables."""
    engine = create_async_engine(TEST_DB_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    await engine.dispose()


# Parse Accept-Language Tests
def test_parse_accept_language_simple():
    """Test parsing simple Accept-Language header."""
    languages = parse_accept_language("en-US,en;q=0.9")
    assert len(languages) == 2
    assert languages[0] == ("en", 1.0)
    assert languages[1] == ("en", 0.9)


def test_parse_accept_language_with_q_values():
    """Test parsing Accept-Language with q-values."""
    languages = parse_accept_language("ar-EG,ar;q=0.9,en;q=0.8,fr;q=0.5")
    assert len(languages) == 4
    # Should be sorted by quality (highest first)
    assert languages[0] == ("ar", 1.0)
    assert languages[1] == ("ar", 0.9)
    assert languages[2] == ("en", 0.8)
    assert languages[3] == ("fr", 0.5)


def test_parse_accept_language_malformed():
    """Test parsing malformed Accept-Language header gracefully."""
    # Should not crash on malformed input
    languages = parse_accept_language("en-US;q=invalid,ar")
    assert len(languages) == 2
    # Invalid q-value defaults to 1.0
    assert ("en", 1.0) in languages
    assert ("ar", 1.0) in languages


def test_parse_accept_language_empty():
    """Test parsing empty Accept-Language header."""
    languages = parse_accept_language("")
    assert len(languages) == 0


def test_parse_accept_language_with_spaces():
    """Test parsing Accept-Language with extra spaces."""
    languages = parse_accept_language("  en-US  ,  ar ; q=0.9  ")
    assert len(languages) == 2
    assert languages[0] == ("en", 1.0)
    assert languages[1] == ("ar", 0.9)


# Locale Detection Precedence Tests
@pytest.mark.asyncio
async def test_locale_precedence_query_param_highest(test_db):
    """Test lang query parameter has highest precedence."""
    request = Mock(spec=Request)
    request.headers = {"accept-language": "en-US"}
    request.cookies = {"locale": "en"}

    # Create user with preferred locale
    user = User(
        username="testuser",
        preferred_locale="en",
    )
    test_db.add(user)
    await test_db.commit()

    # Mock get_current_user_id_optional to return user
    with patch("api.deps.get_current_user_id_optional", return_value=str(user.id)):
        locale = await get_locale(
            request=request,
            lang="ar",  # Explicit query param
            locale_cookie="en",
            accept_language="en-US",
            session=test_db,
        )
        assert locale == "ar"


@pytest.mark.asyncio
async def test_locale_precedence_cookie_second(test_db):
    """Test locale cookie has second precedence."""
    request = Mock(spec=Request)
    request.headers = {"accept-language": "en-US"}

    # Create user with preferred locale
    user = User(
        username="testuser",
        preferred_locale="en",
    )
    test_db.add(user)
    await test_db.commit()

    # Mock get_current_user_id_optional to return user
    with patch("api.deps.get_current_user_id_optional", return_value=str(user.id)):
        locale = await get_locale(
            request=request,
            lang=None,  # No query param
            locale_cookie="ar",  # Cookie present
            accept_language="en-US",
            session=test_db,
        )
        assert locale == "ar"


@pytest.mark.asyncio
async def test_locale_precedence_user_preference_third(test_db):
    """Test user's preferred_locale has third precedence."""
    request = Mock(spec=Request)
    request.headers = {"accept-language": "en-US"}

    # Create user with preferred locale
    user = User(
        username="testuser",
        preferred_locale="ar",
    )
    test_db.add(user)
    await test_db.commit()

    # Mock get_current_user_id_optional to return user
    with patch("api.deps.get_current_user_id_optional", return_value=str(user.id)):
        locale = await get_locale(
            request=request,
            lang=None,  # No query param
            locale_cookie=None,  # No cookie
            accept_language="en-US",
            session=test_db,
        )
        assert locale == "ar"


@pytest.mark.asyncio
async def test_locale_precedence_accept_language_fourth(test_db):
    """Test Accept-Language header has fourth precedence."""
    request = Mock(spec=Request)

    # Mock get_current_user_id_optional to return None (unauthenticated)
    with patch("api.deps.get_current_user_id_optional", return_value=None):
        locale = await get_locale(
            request=request,
            lang=None,  # No query param
            locale_cookie=None,  # No cookie
            accept_language="ar-EG,ar;q=0.9,en;q=0.8",
            session=test_db,
        )
        assert locale == "ar"


@pytest.mark.asyncio
async def test_locale_precedence_default_last(test_db):
    """Test default locale has lowest precedence."""
    request = Mock(spec=Request)

    # Mock get_current_user_id_optional to return None (unauthenticated)
    with patch("api.deps.get_current_user_id_optional", return_value=None):
        locale = await get_locale(
            request=request,
            lang=None,  # No query param
            locale_cookie=None,  # No cookie
            accept_language=None,  # No header
            session=test_db,
        )
        assert locale == settings.DEFAULT_LOCALE


# Locale Validation Tests
@pytest.mark.asyncio
async def test_locale_invalid_query_param_ignored(test_db):
    """Test invalid locale in query param is ignored."""
    request = Mock(spec=Request)

    with patch("api.deps.get_current_user_id_optional", return_value=None):
        locale = await get_locale(
            request=request,
            lang="invalid",  # Invalid locale
            locale_cookie=None,
            accept_language="ar-EG",
            session=test_db,
        )
        # Should fall back to Accept-Language
        assert locale == "ar"


@pytest.mark.asyncio
async def test_locale_invalid_cookie_ignored(test_db):
    """Test invalid locale in cookie is ignored."""
    request = Mock(spec=Request)

    with patch("api.deps.get_current_user_id_optional", return_value=None):
        locale = await get_locale(
            request=request,
            lang=None,
            locale_cookie="invalid",  # Invalid locale
            accept_language="ar-EG",
            session=test_db,
        )
        # Should fall back to Accept-Language
        assert locale == "ar"


# Unauthenticated User Tests
@pytest.mark.asyncio
async def test_locale_unauthenticated_user_uses_cookie(test_db):
    """Test unauthenticated user uses cookie."""
    request = Mock(spec=Request)

    with patch("api.deps.get_current_user_id_optional", return_value=None):
        locale = await get_locale(
            request=request,
            lang=None,
            locale_cookie="ar",
            accept_language="en-US",
            session=test_db,
        )
        assert locale == "ar"


@pytest.mark.asyncio
async def test_locale_unauthenticated_user_uses_accept_language(test_db):
    """Test unauthenticated user falls back to Accept-Language."""
    request = Mock(spec=Request)

    with patch("api.deps.get_current_user_id_optional", return_value=None):
        locale = await get_locale(
            request=request,
            lang=None,
            locale_cookie=None,
            accept_language="ar-EG,ar;q=0.9,en;q=0.8",
            session=test_db,
        )
        assert locale == "ar"


# Accept-Language q-value Parsing Tests
@pytest.mark.asyncio
async def test_locale_accept_language_respects_q_values(test_db):
    """Test Accept-Language respects q-values and picks highest quality."""
    request = Mock(spec=Request)

    with patch("api.deps.get_current_user_id_optional", return_value=None):
        # ar has higher quality than en
        locale = await get_locale(
            request=request,
            lang=None,
            locale_cookie=None,
            accept_language="en;q=0.5,ar;q=0.9",
            session=test_db,
        )
        assert locale == "ar"


@pytest.mark.asyncio
async def test_locale_accept_language_first_supported_locale(test_db):
    """Test Accept-Language picks first supported locale in order."""
    request = Mock(spec=Request)

    with patch("api.deps.get_current_user_id_optional", return_value=None):
        # fr is not supported, ar is first supported locale
        locale = await get_locale(
            request=request,
            lang=None,
            locale_cookie=None,
            accept_language="fr;q=1.0,ar;q=0.9,en;q=0.8",
            session=test_db,
        )
        assert locale == "ar"


# Error Handling Tests
@pytest.mark.asyncio
async def test_locale_user_lookup_failure_continues_to_next_priority(test_db):
    """Test that user lookup failure doesn't crash, continues to next priority."""
    request = Mock(spec=Request)

    # Simulate user lookup failure
    with patch("api.deps.get_current_user_id_optional", side_effect=Exception("DB error")):
        locale = await get_locale(
            request=request,
            lang=None,
            locale_cookie=None,
            accept_language="ar-EG",
            session=test_db,
        )
        # Should fall back to Accept-Language
        assert locale == "ar"


@pytest.mark.asyncio
async def test_locale_malformed_accept_language_continues_to_default(test_db):
    """Test malformed Accept-Language doesn't crash."""
    request = Mock(spec=Request)

    with patch("api.deps.get_current_user_id_optional", return_value=None):
        # Malformed header that might cause parsing issues
        locale = await get_locale(
            request=request,
            lang=None,
            locale_cookie=None,
            accept_language=";;;invalid;;;",
            session=test_db,
        )
        # Should fall back to default
        assert locale == settings.DEFAULT_LOCALE


# Case Sensitivity Tests
@pytest.mark.asyncio
async def test_locale_case_insensitive_query_param(test_db):
    """Test locale query param is case-insensitive."""
    request = Mock(spec=Request)

    with patch("api.deps.get_current_user_id_optional", return_value=None):
        locale = await get_locale(
            request=request,
            lang="AR",  # Uppercase
            locale_cookie=None,
            accept_language=None,
            session=test_db,
        )
        assert locale == "ar"


@pytest.mark.asyncio
async def test_locale_case_insensitive_cookie(test_db):
    """Test locale cookie is case-insensitive."""
    request = Mock(spec=Request)

    with patch("api.deps.get_current_user_id_optional", return_value=None):
        locale = await get_locale(
            request=request,
            lang=None,
            locale_cookie="AR",  # Uppercase
            accept_language=None,
            session=test_db,
        )
        assert locale == "ar"
