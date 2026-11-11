"""Centralized model registry so Alembic autogenerate discovers all domain tables."""

from app.core.database import Base
from app.modules.identity.models import User, UserPreference, UserProfile
from app.modules.moderation.models import AuditLog
from app.modules.organizations.models import (
    Address,
    Organization,
    OrganizationMember,
    OrganizationVerification,
)

__all__ = [
    "Base",
    "User",
    "UserProfile",
    "UserPreference",
    "Address",
    "Organization",
    "OrganizationMember",
    "OrganizationVerification",
    "AuditLog",
]

