"""
Vault-friendly secret loader with fallback to environment variables.

This module provides a unified interface for loading secrets from various sources:
1. Environment variables (for local development)
2. HashiCorp Vault (for production)
3. Azure Key Vault (alternative option)

The loader checks the ENVIRONMENT variable to determine which source to use.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class SecretNotFoundError(Exception):
    """Raised when a secret cannot be found in any configured source."""

    pass


class VaultClient:
    """Stub Vault client for production use."""

    def __init__(self, **config):
        """
        Initialize Vault client with configuration.

        Args:
            **config: Vault configuration parameters
                      (url, token, role_id, secret_id, etc.)
        """
        self.config = config
        self.url = config.get("url")
        self.token = config.get("token")
        self.role_id = config.get("role_id")
        self.secret_id = config.get("secret_id")

        if not self.url:
            raise ValueError("Vault URL is required")

    def get_secret(self, path: str, key: str) -> str:
        """
        Retrieve a secret from Vault.

        Args:
            path: Secret path in Vault
            key: Secret key name

        Returns:
            The secret value

        Raises:
            SecretNotFoundError: If secret doesn't exist
            Exception: For other Vault-related errors
        """
        # For now, raise an exception to indicate Vault integration is needed
        raise NotImplementedError(
            "Vault integration not implemented. "
            "Please configure Vault credentials and install the hvac library."
        )


class AzureKeyVaultClient:
    """Stub Azure Key Vault client for production use."""

    def __init__(self, **config):
        """
        Initialize Azure Key Vault client with configuration.

        Args:
            **config: Azure Key Vault configuration parameters
                      (vault_url, client_id, client_secret, tenant_id, etc.)
        """
        self.config = config
        self.vault_url = config.get("vault_url")
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.tenant_id = config.get("tenant_id")

        if not self.vault_url:
            raise ValueError("Azure Key Vault URL is required")

    def get_secret(self, secret_name: str) -> str:
        """
        Retrieve a secret from Azure Key Vault.

        Args:
            secret_name: Name of the secret

        Returns:
            The secret value

        Raises:
            SecretNotFoundError: If secret doesn't exist
            Exception: For other Key Vault-related errors
        """
        # For now, raise an exception to indicate Key Vault integration is needed
        raise NotImplementedError(
            "Azure Key Vault integration not implemented. "
            "Please configure Azure credentials and install azure-keyvault-secrets library."
        )


def get_secret_loader():
    """
    Factory function to get the appropriate secret loader based on environment.

    Returns:
        A secret loader function
    """
    environment = os.getenv("ENVIRONMENT", "production").lower()

    if environment == "local":
        logger.info("Loading secrets from environment variables (local mode)")
        return load_from_env
    elif environment == "vault":
        logger.info("Loading secrets from HashiCorp Vault")
        try:
            vault_config = {
                "url": os.getenv("VAULT_URL"),
                "token": os.getenv("VAULT_TOKEN"),
                "role_id": os.getenv("VAULT_ROLE_ID"),
                "secret_id": os.getenv("VAULT_SECRET_ID"),
            }
            client = VaultClient(**vault_config)
            return lambda secret_path, secret_key: client.get_secret(
                secret_path, secret_key
            )
        except Exception as e:
            logger.error(f"Failed to initialize Vault client: {e}")
            raise
    elif environment == "azure":
        logger.info("Loading secrets from Azure Key Vault")
        try:
            vault_config = {
                "vault_url": os.getenv("AZURE_KEY_VAULT_URL"),
                "client_id": os.getenv("AZURE_CLIENT_ID"),
                "client_secret": os.getenv("AZURE_CLIENT_SECRET"),
                "tenant_id": os.getenv("AZURE_TENANT_ID"),
            }
            client = AzureKeyVaultClient(**vault_config)
            return lambda secret_name, _: client.get_secret(secret_name)
        except Exception as e:
            logger.error(f"Failed to initialize Azure Key Vault client: {e}")
            raise
    else:
        raise ValueError(
            f"Unknown environment: {environment}. "
            "Supported values: local, vault, azure"
        )


def load_from_env(secret_name: str, secret_key: Optional[str] = None) -> str:
    """
    Load a secret from environment variables.

    Args:
        secret_name: Name of the environment variable
        secret_key: Optional key for nested secrets (not used in env mode)

    Returns:
        The secret value from environment variables

    Raises:
        SecretNotFoundError: If the environment variable is not set
    """
    value = os.getenv(secret_name)
    if value is None:
        raise SecretNotFoundError(
            f"Environment variable '{secret_name}' is not set"
        )
    return value


def get_secret(secret_name: str, secret_key: Optional[str] = None) -> str:
    """
    Load a secret using the configured loader.

    Args:
        secret_name: Name/path of the secret
        secret_key: Optional key for nested secrets

    Returns:
        The secret value

    Raises:
        SecretNotFoundError: If the secret cannot be found
    """
    try:
        loader = get_secret_loader()
        return loader(secret_name, secret_key)
    except Exception as e:
        logger.error(f"Failed to load secret '{secret_name}': {e}")
        raise SecretNotFoundError(
            f"Failed to load secret '{secret_name}': {e}"
        )


def get_secret_with_fallback(
    secret_name: str,
    fallback_env_var: Optional[str] = None,
    secret_key: Optional[str] = None,
) -> str:
    """
    Load a secret with fallback to environment variable.

    Args:
        secret_name: Name/path of the secret
        fallback_env_var: Environment variable name to use as fallback
        secret_key: Optional key for nested secrets

    Returns:
        The secret value

    Raises:
        SecretNotFoundError: If the secret cannot be found in any source
    """
    try:
        # Try to load from secret store first
        return get_secret(secret_name, secret_key)
    except SecretNotFoundError:
        # Fall back to environment variable if provided
        if fallback_env_var:
            logger.info(
                f"Secret '{secret_name}' not found in secret store, "
                f"falling back to environment variable '{fallback_env_var}'"
            )
            return load_from_env(fallback_env_var, secret_key)
        # Re-raise if no fallback is configured
        raise


# Common secrets with environment variable fallbacks
def get_jwt_secret_key() -> str:
    """Get JWT secret key with fallback to JWT_SECRET_KEY env var."""
    return get_secret_with_fallback("jwt/secret-key", "JWT_SECRET_KEY")


def get_database_url() -> str:
    """Get database URL with fallback to DATABASE_URL env var."""
    return get_secret_with_fallback(
        "database/connection-string", "DATABASE_URL"
    )


def get_ldap_password() -> str:
    """Get LDAP password with fallback to LDAP_PASSWORD env var."""
    return get_secret_with_fallback("ldap/password", "LDAP_PASSWORD")


def get_mail_password() -> str:
    """Get mail password with fallback to MAIL_PASSWORD env var."""
    return get_secret_with_fallback("mail/password", "MAIL_PASSWORD")


# Export main function
__all__ = [
    "get_secret",
    "get_secret_with_fallback",
    "get_jwt_secret_key",
    "get_database_url",
    "get_ldap_password",
    "get_mail_password",
    "SecretNotFoundError",
]
