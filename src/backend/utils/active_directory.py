import logging
from typing import List, Optional

from dotenv import load_dotenv
from ldap3 import ALL, SIMPLE, SUBTREE, Connection, Server

from core.config import settings
from utils.app_schemas import DomainAccount

# Load environment variables from the .env file
load_dotenv()

# Set up logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class LDAPAuthenticator:
    """
    A class to authenticate users against an LDAP server and retrieve user attributes.

    Attributes:
        domain (str): The domain of the LDAP server.
        dc (str): The domain controller (DC) hostname or IP address.
    """

    def _get_search_bases(self) -> List[str]:
        """
        Get list of search bases from allowed OUs configuration.

        Returns:
            List of LDAP search base DNs
        """
        allowed_ous = settings.ldap.get_allowed_ous_list()
        base_dn = settings.ldap.base_dn
        ou_template = settings.ldap.ou_path_template

        if not allowed_ous:
            # Fallback to original behavior if no OUs configured
            logger.warning(
                "AD_ALLOWED_OUS not configured, falling back to full Andalusia OU"
            )
            return [f"OU=Andalusia,{base_dn}"]

        search_bases = []
        for ou in allowed_ous:
            # Build the search base using the template
            # Template: "OU=Users,OU={ou},OU=Andalusia"
            ou_path = ou_template.format(ou=ou)
            search_base = f"{ou_path},{base_dn}"
            search_bases.append(search_base)
            logger.debug(f"Added search base for OU '{ou}': {search_base}")

        return search_bases

    def _search_ou(
        self,
        connection: Connection,
        search_base: str,
        search_filter: str,
        paged_size: int = 1000,
    ) -> List[DomainAccount]:
        """
        Search a single OU for enabled domain accounts.

        Args:
            connection: LDAP connection
            search_base: The search base DN
            search_filter: LDAP search filter
            paged_size: Page size for paged results

        Returns:
            List of DomainAccount objects found in this OU
        """
        accounts = []

        try:
            # AD attributes to fetch
            ad_attributes = [
                "sAMAccountName",
                "displayName",
                "title",
                "mail",
                "physicalDeliveryOfficeName",
                "telephoneNumber",
                "manager",
            ]

            connection.search(
                search_base=search_base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=ad_attributes,
                paged_size=paged_size,
            )

            while True:
                for entry in connection.entries:
                    try:
                        # Extract manager CN from DN (e.g., "CN=John Doe,OU=..." -> "John Doe")
                        manager_dn = (
                            entry.manager.value
                            if hasattr(entry, "manager") and entry.manager.value
                            else None
                        )
                        manager_name = None
                        if manager_dn:
                            # Parse CN from DN
                            cn_part = (
                                manager_dn.split(",")[0]
                                if "," in manager_dn
                                else manager_dn
                            )
                            if cn_part.upper().startswith("CN="):
                                manager_name = cn_part[3:]

                        accounts.append(
                            DomainAccount(
                                username=entry.sAMAccountName.value,
                                email=entry.mail.value
                                if hasattr(entry, "mail") and entry.mail.value
                                else None,
                                fullName=entry.displayName.value
                                if hasattr(entry, "displayName")
                                else None,
                                title=entry.title.value
                                if hasattr(entry, "title") and entry.title.value
                                else None,
                                office=entry.physicalDeliveryOfficeName.value
                                if hasattr(entry, "physicalDeliveryOfficeName")
                                and entry.physicalDeliveryOfficeName.value
                                else None,
                                phone=entry.telephoneNumber.value
                                if hasattr(entry, "telephoneNumber")
                                and entry.telephoneNumber.value
                                else None,
                                manager=manager_name,
                            )
                        )
                    except Exception as e:
                        logger.warning(f"Failed to parse entry: {e}")
                        continue

                # Check if there are more pages
                if (
                    "controls" in connection.result
                    and "1.2.840.113556.1.4.319" in connection.result["controls"]
                ):
                    cookie = connection.result["controls"]["1.2.840.113556.1.4.319"][
                        "value"
                    ]["cookie"]
                    if cookie:
                        connection.search(
                            search_base=search_base,
                            search_filter=search_filter,
                            search_scope=SUBTREE,
                            attributes=ad_attributes,
                            paged_size=paged_size,
                            paged_cookie=cookie,
                        )
                    else:
                        break
                else:
                    break

        except Exception as e:
            logger.error(f"Failed to search OU '{search_base}': {e}")

        return accounts

    def get_domain_accounts(self) -> Optional[List[DomainAccount]]:
        """
        Fetch enabled domain users from Active Directory.

        Fetches users only from the OUs specified in AD_ALLOWED_OUS setting.
        Only returns enabled users (not disabled in AD).

        Returns:
            Optional[List[DomainAccount]]: A list of DomainAccount objects
            if successful, otherwise None.
        """
        try:
            DC = settings.ldap.server
            USERNAME = settings.ldap.service_account
            PASSWORD = settings.ldap.service_password

            if not DC or not USERNAME or not PASSWORD:
                logger.error("AD connection settings not configured")
                return None

            # Set up the server and connection
            server = Server(DC, port=389, use_ssl=False, get_info=ALL)
            connection = Connection(
                server,
                user=USERNAME,
                password=PASSWORD,
                authentication=SIMPLE,
                auto_bind=True,
            )

            # Search filter for enabled users only
            # userAccountControl bit 2 (0x2) = ACCOUNTDISABLE
            # The filter excludes users with this bit set
            search_filter = (
                "(&"
                "(objectCategory=person)"
                "(objectClass=user)"
                "(!(userAccountControl:1.2.840.113556.1.4.803:=2))"
                ")"
            )

            # Get search bases from configuration
            search_bases = self._get_search_bases()
            logger.info(f"Fetching users from {len(search_bases)} OU(s)")

            # Collect accounts from all OUs
            domain_accounts = []
            for search_base in search_bases:
                logger.info(f"Searching OU: {search_base}")
                ou_accounts = self._search_ou(
                    connection=connection,
                    search_base=search_base,
                    search_filter=search_filter,
                )
                logger.info(f"Found {len(ou_accounts)} users in {search_base}")
                domain_accounts.extend(ou_accounts)

            connection.unbind()

            logger.info(f"Total users fetched from AD: {len(domain_accounts)}")
            return domain_accounts if domain_accounts else None

        except Exception as e:
            logger.error(f"Failed to fetch domain accounts: {e}")
            return None
