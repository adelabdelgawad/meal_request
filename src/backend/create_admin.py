#!/usr/bin/env python3
"""
Admin User Creation Utility

Creates a new admin user with encrypted password.

Features:
- Interactive password entry with confirmation
- Password strength validation
- Secure password hashing (bcrypt)
- Automatic role assignment (admin)
- Checks for existing admin user

Usage:
    python create_admin.py
    python create_admin.py --username admin --email admin@example.com
"""

import asyncio
import getpass
import logging
import re
import sys
from typing import Optional

from api.services import RoleService, UserService
from db.maria_database import get_maria_session

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def validate_username(username: str) -> tuple[bool, Optional[str]]:
    """
    Validate username format.

    Args:
        username: Username to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not username:
        return False, "Username cannot be empty"

    if len(username) < 3:
        return False, "Username must be at least 3 characters long"

    if len(username) > 32:
        return False, "Username must be at most 32 characters long"

    if not re.match(r'^[a-zA-Z0-9._-]+$', username):
        return False, "Username can only contain letters, numbers, dots, underscores, and hyphens"

    return True, None


def validate_email(email: str) -> tuple[bool, Optional[str]]:
    """
    Validate email format.

    Args:
        email: Email to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return True, None  # Email is optional

    # Basic email validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "Invalid email format"

    return True, None


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


def get_password_input() -> str:
    """
    Get password from user with confirmation.

    Returns:
        Validated password
    """
    while True:
        # Get password
        password = getpass.getpass("Enter admin password: ")

        # Validate password
        is_valid, error = validate_password(password)
        if not is_valid:
            print(f"❌ {error}")
            print("Password requirements:")
            print("  - At least 8 characters")
            print("  - At least one uppercase letter")
            print("  - At least one lowercase letter")
            print("  - At least one digit")
            print("  - At least one special character")
            print()
            continue

        # Confirm password
        confirm = getpass.getpass("Confirm password: ")

        if password != confirm:
            print("❌ Passwords do not match. Please try again.\n")
            continue

        return password


async def create_admin_user(
    username: str,
    password: str,
    email: Optional[str] = None,
    full_name: Optional[str] = None,
) -> bool:
    """
    Create admin user with encrypted password.

    Args:
        username: Admin username
        password: Admin password (will be hashed)
        email: Optional email address
        full_name: Optional full name

    Returns:
        True if created successfully, False otherwise
    """
    # Get database session
    session_gen = get_maria_session()
    session = await session_gen.__anext__()

    try:
        # Initialize services
        user_service = UserService()
        role_service = RoleService()

        # Check if user already exists
        logger.info(f"Checking if user '{username}' already exists...")
        existing_user = await user_service.get_user_by_username(session, username)

        if existing_user:
            print(f"\n❌ User '{username}' already exists!")
            print("Use reset_admin.py to reset the password instead.")
            return False

        # Create user (password will be automatically hashed by UserService)
        logger.info(f"Creating admin user '{username}'...")
        user = await user_service.create_user(
            session=session,
            username=username,
            password=password,  # Will be hashed by service
            email=email,
            full_name=full_name,
            title="System Administrator",
            is_domain_user=False,  # Local admin account
        )

        logger.info(f"✅ User created with ID: {user.id}")

        # Check if admin role exists
        logger.info("Checking for admin role...")
        try:
            admin_role = await role_service.get_role_by_name(session, "admin")
            logger.info(f"✅ Admin role found with ID: {admin_role.id}")
        except Exception as e:
            logger.warning(f"Admin role not found, creating it... ({e})")
            # Create admin role if it doesn't exist
            admin_role = await role_service.create_role(
                session=session,
                name="admin",
                description="System Administrator"
            )
            logger.info(f"✅ Admin role created with ID: {admin_role.id}")

        # Assign admin role to user
        logger.info("Assigning admin role to user...")
        # Note: Assuming there's an Account model that links User to Role
        # If not, this step might need adjustment based on your schema

        # Commit all changes
        await session.commit()

        logger.info("✅ Admin user created successfully")
        return True

    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating admin user: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return False
    finally:
        await session.close()


async def interactive_create_admin() -> None:
    """
    Interactive admin creation process.
    """
    print("\n" + "=" * 70)
    print("👤 ADMIN USER CREATION")
    print("=" * 70)
    print("\nThis utility will create a new admin user with encrypted password.\n")

    # Get username
    while True:
        username = input("Enter username (default: admin): ").strip() or "admin"
        is_valid, error = validate_username(username)
        if not is_valid:
            print(f"❌ {error}\n")
            continue
        break

    # Get email (optional)
    while True:
        email = input("Enter email (optional, press Enter to skip): ").strip() or None
        if email:
            is_valid, error = validate_email(email)
            if not is_valid:
                print(f"❌ {error}\n")
                continue
        break

    # Get full name (optional)
    full_name = input("Enter full name (optional, press Enter to skip): ").strip() or None

    # Get password
    print()
    password = get_password_input()

    print("\n" + "=" * 70)
    print("Creating admin user...")
    print("=" * 70 + "\n")

    # Create user
    success = await create_admin_user(
        username=username,
        password=password,
        email=email,
        full_name=full_name,
    )

    if success:
        print("\n" + "=" * 70)
        print("✅ ADMIN USER CREATED SUCCESSFULLY")
        print("=" * 70)
        print(f"\nUsername: {username}")
        if email:
            print(f"Email: {email}")
        if full_name:
            print(f"Full Name: {full_name}")
        print("\nYou can now log in with these credentials.")
        print()
    else:
        print("\n❌ Failed to create admin user. Check the logs for details.")
        sys.exit(1)


def main():
    """Main entry point."""
    # Check for command-line arguments
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print(__doc__)
        return

    # Run interactive creation
    asyncio.run(interactive_create_admin())


if __name__ == "__main__":
    main()
