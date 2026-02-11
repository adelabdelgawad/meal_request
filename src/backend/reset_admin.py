#!/usr/bin/env python3
"""
Admin Password Reset Utility

Resets the password for an existing admin user.

Features:
- Interactive password entry with confirmation
- Password strength validation
- Secure password hashing (bcrypt)
- Finds admin user by username or email
- Updates password in database

Usage:
    python reset_admin.py
    python reset_admin.py --username admin
"""

import argparse
import asyncio
import getpass
import logging
import re
import sys
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from api.services import UserService
from db.database import get_maria_session

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def validate_password(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength.

    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password cannot be empty"

    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if len(password) > 128:
        return False, "Password must be at most 128 characters long"

    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one digit"

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)"

    return True, None


def show_password_requirements():
    """Display password requirements to user."""
    print("\nPassword requirements:")
    print("  ✓ At least 8 characters")
    print("  ✓ At least one uppercase letter (A-Z)")
    print("  ✓ At least one lowercase letter (a-z)")
    print("  ✓ At least one digit (0-9)")
    print("  ✓ At least one special character (!@#$%^&*(),.?\":{}|<>)")
    print()


def get_password_input() -> str:
    """
    Get password from user with confirmation.

    Returns:
        Validated password
    """
    show_password_requirements()

    while True:
        # Get password
        password = getpass.getpass("Enter new password: ")

        # Validate password
        is_valid, error = validate_password(password)
        if not is_valid:
            print(f"❌ {error}")
            print("Please try again.\n")
            continue

        # Confirm password
        confirm = getpass.getpass("Confirm new password: ")

        if password != confirm:
            print("❌ Passwords do not match. Please try again.\n")
            continue

        return password


async def find_admin_user(session: AsyncSession, identifier: str) -> Optional:
    """
    Find admin user by username or email.

    Args:
        session: Database session
        identifier: Username or email

    Returns:
        User object if found, None otherwise
    """
    user_service = UserService()

    # Try by username first
    try:
        user = await user_service.get_user_by_username(session, identifier)
        if user:
            return user
    except Exception:
        pass

    # Try by email
    try:
        user = await user_service.get_user_by_email(session, identifier)
        if user:
            return user
    except Exception:
        pass

    return None


async def reset_user_password(username_or_email: str, new_password: str) -> bool:
    """
    Reset password for admin user.

    Args:
        username_or_email: Username or email of the user
        new_password: New password (will be hashed)

    Returns:
        True if reset successfully, False otherwise
    """
    # Get database session
    session_gen = get_maria_session()
    session = await session_gen.__anext__()

    try:
        # Initialize service
        user_service = UserService()

        # Find user
        logger.info(f"Looking for user: {username_or_email}")
        user = await find_admin_user(session, username_or_email)

        if not user:
            print(f"\n❌ User '{username_or_email}' not found!")
            print("Please check the username or email and try again.")
            return False

        logger.info(f"Found user: {user.username} (ID: {user.id})")

        # Display user info for confirmation
        print("\nFound user:")
        print(f"  Username: {user.username}")
        print(f"  ID: {user.id}")
        if hasattr(user, 'email') and user.email:
            print(f"  Email: {user.email}")
        if hasattr(user, 'full_name') and user.full_name:
            print(f"  Full Name: {user.full_name}")

        # Ask for final confirmation
        print(f"\nAre you sure you want to reset the password for '{user.username}'?")
        response = input("Type 'YES' to confirm: ").strip()

        if response != "YES":
            print("\n❌ Password reset cancelled.")
            return False

        # Update password (will be hashed by service)
        logger.info("Updating password...")
        await user_service.update_user(
            session=session,
            user_id=user.id,
            password=new_password,  # Will be hashed by service
        )

        # Commit changes
        await session.commit()

        logger.info("✅ Password reset successfully")
        return True

    except Exception as e:
        await session.rollback()
        logger.error(f"Error resetting password: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return False
    finally:
        await session.close()


async def list_admin_users() -> None:
    """
    List all admin users in the database.
    """
    session_gen = get_maria_session()
    session = await session_gen.__anext__()

    try:
        user_service = UserService()

        # Get all users (you might want to filter for admins only)
        logger.info("Fetching all users...")
        users, total = await user_service.list_users(session, page=1, per_page=100)

        if not users:
            print("\nNo users found in database.")
            return

        print("\n" + "=" * 70)
        print(f"USERS IN DATABASE ({total} total)")
        print("=" * 70)

        for i, user in enumerate(users, 1):
            print(f"\n{i}. Username: {user.username}")
            print(f"   ID: {user.id}")
            if hasattr(user, 'email') and user.email:
                print(f"   Email: {user.email}")
            if hasattr(user, 'full_name') and user.full_name:
                print(f"   Full Name: {user.full_name}")
            if hasattr(user, 'is_domain_user'):
                print(f"   Type: {'Domain User' if user.is_domain_user else 'Local User'}")

        print()

    except Exception as e:
        logger.error(f"Error listing users: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
    finally:
        await session.close()


async def interactive_reset_password() -> None:
    """
    Interactive password reset process.
    """
    print("\n" + "=" * 70)
    print("🔐 ADMIN PASSWORD RESET")
    print("=" * 70)
    print("\nThis utility will reset the password for an existing user.\n")

    # Ask if user wants to see list of users first
    show_list = input("Do you want to see a list of all users? (y/N): ").strip().lower()
    if show_list in ['y', 'yes']:
        await list_admin_users()

    # Get username or email
    print("\nEnter the username or email of the user to reset:")
    identifier = input("> ").strip()

    if not identifier:
        print("❌ Username/email cannot be empty.")
        return

    # Get new password
    print()
    new_password = get_password_input()

    print("\n" + "=" * 70)
    print("Resetting password...")
    print("=" * 70 + "\n")

    # Reset password
    success = await reset_user_password(identifier, new_password)

    if success:
        print("\n" + "=" * 70)
        print("✅ PASSWORD RESET SUCCESSFULLY")
        print("=" * 70)
        print(f"\nThe password for '{identifier}' has been updated.")
        print("You can now log in with the new password.")
        print()
    else:
        print("\n❌ Failed to reset password. Check the logs for details.")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Reset admin user password",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--username",
        "-u",
        help="Username or email of the user to reset"
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List all users and exit"
    )

    args = parser.parse_args()

    # List users mode
    if args.list:
        asyncio.run(list_admin_users())
        return

    # Non-interactive mode
    if args.username:
        async def reset_with_username():
            password = get_password_input()
            await reset_user_password(args.username, password)

        asyncio.run(reset_with_username())
        return

    # Interactive mode
    asyncio.run(interactive_reset_password())


if __name__ == "__main__":
    main()
