"""app/services/container.py — Dependency injection container for services.

exports: ServiceContainer
used_by: app/main.py → create_app()
rules:   must lazy-initialize heavy services; handle circular dependencies via properties
agent:   Product Architect | 2024-03-30 | implemented DI container with lazy loading
         message: "consider adding service lifecycle management for cleanup on shutdown"
"""

import logging
from typing import Optional

from app.database import Database
from app.redis import RedisClient
from app.config import Config

logger = logging.getLogger(__name__)


class ServiceContainer:
    """Container for all business logic services.
    
    Rules:
        Provides centralized access to all services
        Handles service initialization with dependencies
        Supports lazy initialization for heavy services
        Singleton services - one instance per container
    """
    
    def __init__(
        self,
        db: Database,
        redis: RedisClient,
        config: Config,
    ):
        """Initialize service container.
        
        Args:
            db: Database connection manager
            redis: Redis client
            config: Application configuration
        """
        self._db = db
        self._redis = redis
        self._config = config
        
        # Service instances (initialized lazily)
        self._auth_service: Optional['AuthService'] = None
        self._user_service: Optional['UserService'] = None
        self._organization_service: Optional['OrganizationService'] = None
        self._agent_service: Optional['AgentService'] = None
        self._task_service: Optional['TaskService'] = None
        self._billing_service: Optional['BillingService'] = None
        self._agno_integration: Optional['AgnoIntegrationService'] = None
        self._stripe_integration: Optional['StripeIntegrationService'] = None
        self._scheduler_service: Optional['SchedulerService'] = None
        
        logger.info("Service container initialized")
    
    @property
    def db(self) -> Database:
        """Get database connection manager."""
        return self._db
    
    @property
    def redis(self) -> RedisClient:
        """Get Redis client."""
        return self._redis
    
    @property
    def config(self) -> Config:
        """Get application configuration."""
        return self._config
    
    @property
    def auth(self) -> 'AuthService':
        """Get authentication service."""
        if self._auth_service is None:
            from .auth_service import AuthService
            self._auth_service = AuthService(self)
        return self._auth_service
    
    @property
    def users(self) -> 'UserService':
        """Get user service."""
        if self._user_service is None:
            from .user_service import UserService
            self._user_service = UserService(self)
        return self._user_service
    
    @property
    def organizations(self) -> 'OrganizationService':
        """Get organization service."""
        if self._organization_service is None:
            from .organization_service import OrganizationService
            self._organization_service = OrganizationService(self)
        return self._organization_service
    
    @property
    def agents(self) -> 'AgentService':
        """Get agent service."""
        if self._agent_service is None:
            from .agent_service import AgentService
            self._agent_service = AgentService(self)
        return self._agent_service
    
    @property
    def tasks(self) -> 'TaskService':
        """Get task service."""
        if self._task_service is None:
            from .task_service import TaskService
            self._task_service = TaskService(self)
        return self._task_service
    
    @property
    def billing(self) -> 'BillingService':
        """Get billing service."""
        if self._billing_service is None:
            from .billing_service import BillingService
            self._billing_service = BillingService(self)
        return self._billing_service
    
    @property
    def agno(self) -> 'AgnoIntegrationService':
        """Get Agno integration service."""
        if self._agno_integration is None:
            from .agno_integration import AgnoIntegrationService
            self._agno_integration = AgnoIntegrationService(self)
        return self._agno_integration
    
    @property
    def stripe(self) -> 'StripeIntegrationService':
        """Get Stripe integration service."""
        if self._stripe_integration is None:
            from .stripe_integration import StripeIntegrationService
            self._stripe_integration = StripeIntegrationService(self)
        return self._stripe_integration
    
    @property
    def scheduler(self) -> 'SchedulerService':
        """Get scheduler service."""
        if self._scheduler_service is None:
            from .scheduler_service import SchedulerService
            self._scheduler_service = SchedulerService(self)
        return self._scheduler_service
    
    async def startup(self) -> None:
        """Initialize all services that need async startup.
        
        Rules:
            Called during application startup
            Initializes services that require async initialization
        """
        logger.info("Starting up services...")
        
        # Initialize scheduler service
        if self._scheduler_service:
            await self._scheduler_service.start()
        
        # Initialize other async services here
        
        logger.info("Services startup complete")
    
    async def shutdown(self) -> None:
        """Cleanup all services that need async shutdown.
        
        Rules:
            Called during application shutdown
            Cleans up resources and connections
        """
        logger.info("Shutting down services...")
        
        # Shutdown scheduler service
        if self._scheduler_service:
            await self._scheduler_service.stop()
        
        # Cleanup other services here
        
        logger.info("Services shutdown complete")