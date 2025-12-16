"""
Internal Auth Schemas - Service-to-service authentication models.

Provides request/response models for internal service token management.
"""

from typing import Dict, List, Optional

from pydantic import Field, ConfigDict

from api.schemas._base import CamelModel


class InternalTokenBase(CamelModel):
    """Base model for internal token data."""

    service_name: str = Field(..., description="Name of the service")
    user_id: Optional[str] = Field(None, description="Optional user ID")
    permissions: List[str] = Field(default_factory=list, description="Service permissions")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")


class InternalTokenCreate(InternalTokenBase):
    """Request model for creating an internal service token."""

    pass


class InternalTokenResponse(CamelModel):
    """Response model for internal token issuance."""

    model_config = ConfigDict(from_attributes=True)

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    service_name: str = Field(..., description="Service name")
    issued_at: str = Field(..., description="Token issuance timestamp")
    expires_at: str = Field(..., description="Token expiration timestamp")
    token_type_label: str = Field(default="internal_service", description="Token type label")


class InternalTokenVerifyRequest(CamelModel):
    """Request model for token verification."""

    token: str = Field(..., description="Token to verify")


class InternalTokenVerifyResponse(CamelModel):
    """Response model for token verification."""

    valid: bool = Field(..., description="Token validity status")
    claims: Optional[Dict] = Field(None, description="Token claims if valid")
    error: Optional[str] = Field(None, description="Error message if invalid")
    service_name: Optional[str] = Field(None, description="Service name from token")
    expires_at: Optional[str] = Field(None, description="Token expiration time")


class ServiceHealthResponse(CamelModel):
    """Health check response model."""

    service: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    features: Dict[str, bool] = Field(..., description="Available features")
    configuration: Dict = Field(..., description="Service configuration")


class ServiceConfigResponse(CamelModel):
    """Service configuration response model."""

    service_name: str = Field(..., description="Service name")
    endpoints: Dict[str, str] = Field(..., description="Available endpoints")
    requirements: Dict[str, str] = Field(..., description="API requirements")
