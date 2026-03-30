"""app/services/__init__.py — Service layer container and exports.

exports: ServiceContainer, AuthService, UserService, AgentService, TaskService, BillingService
used_by: app/main.py → create_app(), API endpoints via dependency injection
rules:   all services must be stateless; business logic only, no HTTP concerns
agent:   Product Architect | 2024-03-30 | created service container pattern
         message: "verify that service dependencies don't create circular references"
"""

from .auth_service import AuthService
from .user_service import UserService
from .organization_service import OrganizationService
from .agent_service import AgentService
from .task_service import TaskService
from .billing_service import BillingService
from .agno_integration import AgnoIntegrationService
from .stripe_integration import StripeIntegrationService
from .scheduler_service import SchedulerService
from .container import ServiceContainer

__all__ = [
    "ServiceContainer",
    "AuthService",
    "UserService",
    "OrganizationService",
    "AgentService",
    "TaskService",
    "BillingService",
    "AgnoIntegrationService",
    "StripeIntegrationService",
    "SchedulerService",
]