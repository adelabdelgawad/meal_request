import logging
import traceback
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from ldap3 import ALL, SIMPLE, Connection, Server

from core.config import settings
from utils.app_schemas import UserAttributes
from utils.ad_client import get_ad_client, ADAuthTimeout, ADAuthUnavailable, ADAuthError

# Conditional import for bonsai (async LDAP client)
try:
    import bonsai
    from bonsai import LDAPSearchScope

    BONSAI_AVAILABLE = True
except ImportError:
    BONSAI_AVAILABLE = False
    LDAPSearchScope = None

# Load environment variables from the .env file
load_dotenv()

# Set up logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables
DOMAIN = settings.ldap.domain
DC = settings.ldap.server


class LDAPAuthenticator:
    """
    A class to authenticate users against an LDAP server.

    Attributes:
        domain (str): The domain of the LDAP server.
        dc (str): The domain controller (DC) hostname or IP address.
    """

    def __init__(self, domain: str, dc: str):
        self.domain = domain
        self.dc = dc

    def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate a user against the LDAP server using simple bind.

        Args:
            username (str): The username to authenticate.
            password (str): The password for the given username.

        Returns:
            bool: True if authenticated successfully, otherwise False.
        """
        connection = None
        try:
            server = Server(self.dc, port=389, use_ssl=False, get_info=ALL)
            connection = Connection(
                server,
                user=f"{username}@{self.domain}",
                password=password,
                authentication=SIMPLE,
                auto_bind=True,
            )
            return True

        except Exception as e:
            logger.error(
                f"Authentication failed for user {username}: {e}",
                exc_info=True,
            )
            return False

        finally:
            if connection:
                connection.unbind()


class AuthDependency:
    """
    Dependency for FastAPI to authenticate users using LDAP.

    Attributes:
        authenticator (LDAPAuthenticator): The LDAPAuthenticator instance to authenticate users.
    """

    def __init__(self, authenticator: LDAPAuthenticator):
        self.authenticator = authenticator

    async def __call__(
        self, credentials: HTTPBasicCredentials = Depends(HTTPBasic())
    ) -> str:
        """
        Authenticate the user via LDAP using the provided credentials.

        **CRITICAL FIX:** Uses non-blocking AD client instead of direct sync call.

        Args:
            credentials (HTTPBasicCredentials): Credentials extracted by FastAPI's HTTPBasic security scheme.

        Returns:
            str: The authenticated username.

        Raises:
            HTTPException: If authentication fails.
        """
        ad_client = get_ad_client()
        try:
            user_attrs = await ad_client.authenticate(
                credentials.username, credentials.password
            )
            if not user_attrs:
                raise HTTPException(status_code=401, detail="Invalid credentials")
        except (ADAuthTimeout, ADAuthUnavailable):
            raise HTTPException(
                status_code=503, detail="Authentication service temporarily unavailable"
            )
        except ADAuthError as e:
            logger.error(f"AD authentication error: {e}")
            raise HTTPException(status_code=500, detail="Authentication service error")
        return credentials.username


async def get_user_attributes(username: str) -> Optional[UserAttributes]:
    """
    Fetches and returns user attributes for a given username from Active Directory.

    Args:
        username (str): The username to query.

    Returns:
        Optional[UserAttributes]: A UserAttributes object if the user is found, otherwise None.
    """
    if not BONSAI_AVAILABLE:
        logger.warning("bonsai not available - returning None for user attributes")
        return None

    try:
        # Create LDAP client with service account credentials
        client = bonsai.LDAPClient(f"ldap://{DC}")
        client.set_credentials(
            "SIMPLE",
            user=f"{settings.ldap.service_account}@{DOMAIN}",
            password=settings.ldap.service_password,
        )

        # Connect with async support using context manager
        async with client.connect(is_async=True) as conn:
            # Search for user - search() returns results directly
            results = await conn.search(
                base="DC=andalusia,DC=loc",
                scope=LDAPSearchScope.SUBTREE,
                filter_exp=f"(sAMAccountName={username})",
                attrlist=["displayName", "mail", "telephoneNumber", "title"],
            )

            if results:
                user = results[0]
                return UserAttributes(
                    display_name=user.get("displayName", [None])[0],
                    telephone=user.get("telephoneNumber", [None])[0],
                    mail=user.get("mail", [None])[0],
                    title=user.get("title", [None])[0],
                )
            return None
    except Exception as e:
        logger.error(f"Error fetching user attributes for {username}: {e}")
        logger.debug(traceback.format_exc())
        return None


# Initialize the LDAP authenticator with the domain and DC from environment variables
ldap_authenticator = LDAPAuthenticator(DOMAIN, DC)

# Dependency to check LDAP authentication in FastAPI
security = AuthDependency(ldap_authenticator)


async def authenticate(username: str, password: str) -> Optional[UserAttributes]:
    """
    Check LDAP authentication for the given username and password.

    **CRITICAL FIX:** Uses non-blocking AD client with timeouts and circuit breaker.

    Args:
        username (str): The username to authenticate.
        password (str): The password for the username.

    Returns:
        Optional[UserAttributes]: User attributes if authenticated, otherwise None.
    """
    ad_client = get_ad_client()
    try:
        return await ad_client.authenticate(username, password)
    except (ADAuthTimeout, ADAuthUnavailable, ADAuthError) as e:
        logger.warning(f"AD authentication failed for {username}: {e}")
        return None
