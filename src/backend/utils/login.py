import logging
import traceback
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from api.services.role_service import RoleService
from api.services.security_user_service import SecurityUserService
from api.services.user_service import UserService
from core.security import verify_password
from db.schemas import UserCreate, RolePermissionCreate
from db.schemas import User as UserSchema
from utils.app_schemas import UserAttributes
from utils.custom_exceptions import AuthorizationError
from utils.ldap import authenticate

logger = logging.getLogger(__name__)


class Login:
    """
    Handles user authentication and account management.
    Uses domain (LDAP) authentication for regular users and local authentication for admin only.

    Attributes:
        session (AsyncSession): Database session for CRUD operations.
        username (str): Username for authentication.
        password (Optional[str]): Password for authentication.
        is_authorized (bool): Indicates if the user has necessary permissions.
        is_authenticated (bool): Indicates if the user is successfully authenticated.
        account (Optional[UserSchema]): The authenticated user's account information.
    """

    def __init__(
        self,
        session: AsyncSession,
        username: str,
        password: Optional[str] = None,
    ) -> None:
        self.session: AsyncSession = session
        self.username: str = username
        self.password: Optional[str] = password

        self.is_authorized: bool = False
        self.is_authenticated: bool = False
        self.user: Optional[UserSchema] = None

        # Initialize services
        self._user_service = UserService()
        self._security_user_service = SecurityUserService()
        self._role_service = RoleService()

    async def authenticate(self) -> None:
        """
        Authenticates the user with the following logic:
        1. Check if user exists as local admin (is_super_admin=True) in database
        2. If local admin exists, authenticate using local password only (no LDAP)
        3. If not a local admin, authenticate via domain (LDAP)

        This ensures admin users always authenticate against the database,
        while regular users authenticate via Active Directory/LDAP.
        """
        logger.info(f"Starting authentication for user: {self.username}")

        try:
            # First, check if this is a local admin user
            existing_user = await self._user_service._repo.read_account(
                self.session, username=self.username
            )

            if existing_user and existing_user.is_super_admin:
                # This is a local admin - authenticate against database only (skip LDAP)
                logger.info(
                    f"User '{self.username}' identified as local admin. Using database authentication only."
                )
                await self._authenticate_local_user()
            else:
                # Not a local admin - try domain authentication
                logger.info(
                    f"User '{self.username}' not a local admin. Using domain authentication."
                )
                authenticated = await self._authenticate_domain_user()
                if not authenticated:
                    logger.warning(
                        f"Domain authentication failed for user: {self.username}"
                    )

            if self.user:
                self.is_authenticated = True
                logger.info(
                    f"User '{self.username}' authenticated successfully."
                )
            else:
                logger.warning(
                    f"Authentication failed for user: {self.username}"
                )
        except AuthorizationError:
            raise AuthorizationError(
                "You are not Authorized to Access the System"
            )
        except Exception as e:
            logger.error(
                f"Authentication process failed for user '{
                         self.username}'. Error: {e}"
            )
            logger.debug(traceback.format_exc())

    async def _authenticate_domain_user(self) -> bool:
        """
        Authenticates the user against the domain using LDAP.
        If successful, ensures the account exists locally, creating it if necessary.

        Returns:
            bool: True if authentication and account setup are successful, False otherwise.
        """
        try:
            logger.info(
                f"Attempting domain authentication for user: {
                        self.username}"
            )
            domain_user: Optional[UserAttributes] = await authenticate(
                self.username, self.password
            )

            if not domain_user:
                logger.warning(
                    f"LDAP authentication failed for user: {
                               self.username}"
                )
                return False

            existing_user = await self._user_service._repo.read_account(
                self.session, username=self.username
            )
            if existing_user:
                # Activate pre-created user account on first login
                if not existing_user.is_active:
                    from datetime import datetime, timezone

                    existing_user.is_active = True
                    existing_user.title = domain_user.title  # Update from LDAP
                    existing_user.updated_at = datetime.now(timezone.utc)
                    await self.session.commit()
                    await self.session.refresh(existing_user)

                    logger.info(
                        f"Activated pre-created user account: {self.username}"
                    )

                self.user = UserSchema.model_validate(existing_user)
                logger.info(
                    f"Local account found for domain user: {
                            self.username}"
                )
                return True

            # Create local account if it doesn't exist
            # Strategy A: Check SecurityUser only for HRIS users, not manual users
            hris_security_user = await self._security_user_service.get_by_username(
                self.session, user_name=self.username
            )
            if not hris_security_user:
                logger.warning(
                    f"No security user found for domain user: {self.username}. "
                    f"This user may be a manual or LDAP-only user."
                )
                raise AuthorizationError("No HRIS security record found. Please contact your administrator.")

            new_user_data = UserCreate(
                username=self.username,
                title=domain_user.title,
                is_domain_user=True,
                is_super_admin=False,
            )
            new_user = await self._user_service._repo.create_account(
                self.session, new_user_data
            )

            if new_user:
                # Lookup Requester role dynamically (roles use UUID primary keys)
                from api.repositories.role_repository import RoleRepository

                role_repo = RoleRepository()
                requester_role = await role_repo.get_by_name_en(self.session, "Requester")

                if requester_role:
                    await self._role_service.create_role_permission(
                        self.session,
                        RolePermissionCreate(role_id=str(requester_role.id), user_id=new_user.id),
                    )
                else:
                    logger.error("Requester role not found - cannot assign default role")

                self.user = UserSchema.model_validate(new_user)
                logger.info(
                    f"Local account created for domain user: {
                            self.username}"
                )
                return True

            logger.error(
                f"Failed to create local account for user: {
                         self.username}"
            )
            return False

        except AuthorizationError:
            raise AuthorizationError()

        except Exception as e:
            logger.error(
                f"Domain authentication error for user '{
                         self.username}'. Error: {e}"
            )
            logger.debug(traceback.format_exc())
            return False

    async def _authenticate_local_user(self) -> None:
        """
        Authenticates the user against the local database with password verification.
        Only admin users (is_super_admin=True) are allowed to use local authentication.
        Password is verified using bcrypt hash comparison.
        """
        try:
            logger.info(
                f"Attempting local authentication for user: {
                        self.username}"
            )
            account = await self._user_service._repo.read_account(
                self.session, username=self.username
            )

            if not account:
                logger.warning(
                    f"No local account found for user: {
                               self.username}"
                )
                return

            # Only allow local authentication for admin users
            if not account.is_super_admin:
                logger.warning(
                    f"Local authentication denied for non-admin user: {
                               self.username}"
                )
                return

            # Verify password exists and matches
            if not account.password:
                logger.warning(
                    f"Admin account '{self.username}' has no password set"
                )
                return

            if not self.password:
                logger.warning(
                    f"No password provided for admin user: {self.username}"
                )
                return

            # Verify password using bcrypt
            if not verify_password(self.password, account.password):
                logger.warning(
                    f"Invalid password for admin user: {self.username}"
                )
                return

            # Authentication successful
            self.user = UserSchema.model_validate(account)
            logger.info(
                f"Admin user '{self.username}' authenticated successfully with password"
            )

        except Exception as e:
            logger.error(
                f"Local authentication error for user '{
                         self.username}'. Error: {e}"
            )
            logger.debug(traceback.format_exc())
