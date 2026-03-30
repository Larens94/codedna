"""__init__.py — Pydantic schemas for API validation.

exports: all schemas for request/response validation
used_by: all API routers
rules:   must separate request/response schemas; must not include ORM relationships
agent:   BackendEngineer | 2024-01-15 | created schema package structure
         message: "ensure all schemas have proper validation and documentation"
"""

from .auth import *
from .agents import *
from .billing import *
from .scheduler import *
from .users import *

__all__ = [
    # Auth schemas
    "UserCreate", "UserLogin", "UserResponse", "Token", "TokenData", "PasswordChange",
    # Agent schemas
    "AgentCreate", "AgentUpdate", "AgentResponse", "AgentRunCreate", "AgentRunResponse",
    # Billing schemas
    "CreditPurchase", "InvoiceResponse", "TransactionResponse", "StripeWebhook",
    # Scheduler schemas
    "ScheduledTaskCreate", "ScheduledTaskUpdate", "ScheduledTaskResponse", "TaskRunResponse",
    # User schemas
    "ProfileUpdate", "OrgCreate", "OrgInvite", "OrgMemberResponse", "UsageStats",
]