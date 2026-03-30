"""app/api/v1/schemas/__init__.py — Pydantic schemas for API requests and responses.

exports: all schemas for API validation
used_by: all API endpoint modules for request/response validation
rules:   all schemas must use proper field validation; response schemas must exclude sensitive data
agent:   BackendEngineer | 2024-03-31 | added all schema modules
         message: "consider generating OpenAPI examples for all response schemas"
"""

from .base import BaseSchema, PaginationParams, PaginatedResponse
from .user import (
    UserCreate, UserUpdate, PasswordChange, UserResponse, 
    UserWithOrganizationsResponse, UserOrganizationInfo, UserListResponse
)
from .organization import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    OrganizationStats, OrganizationWithStatsResponse,
    OrganizationMemberCreate, OrganizationMemberInvite, OrganizationMemberUpdate,
    OrganizationMemberResponse, OrganizationListResponse, OrganizationMemberListResponse
)
from .agent import (
    ModelProvider, MessageRole,
    AgentCreate, AgentUpdate, AgentResponse, AgentRunRequest, AgentRunResponse,
    AgentSessionCreate, AgentSessionResponse, SessionMessageCreate, SessionMessageResponse,
    AgentListResponse, AgentSessionListResponse, SessionMessageListResponse
)
from .task import (
    TaskType, TaskStatus, TaskCreate, TaskUpdate, TaskSchedule, TaskResponse,
    TaskStats, TaskListResponse
)
from .billing import (
    InvoiceStatus, InvoiceResponse, LineItemResponse, InvoiceWithLineItemsResponse,
    PaymentIntentCreate, PaymentMethodResponse, SubscriptionCreate, SubscriptionResponse,
    CreditPurchaseCreate, CreditBalanceResponse, InvoiceListResponse, PaymentMethodListResponse
)
from .usage import (
    UsageMetric, UsageRecordResponse, UsageQueryParams, UsageStatsResponse,
    UsageExportRequest, UsageAlertCreate, UsageAlertResponse, UsageListResponse
)
from .admin import (
    AdminUserUpdate, AdminOrganizationUpdate, SystemStatsResponse,
    AuditLogQueryParams, AuditLogEntryResponse, AdminBillingAdjustment,
    AdminBillingAdjustmentResponse, AdminJobCreate, AdminJobResponse,
    AuditLogListResponse
)

__all__ = [
    # Base
    "BaseSchema", "PaginationParams", "PaginatedResponse",
    
    # User
    "UserCreate", "UserUpdate", "PasswordChange", "UserResponse",
    "UserWithOrganizationsResponse", "UserOrganizationInfo", "UserListResponse",
    
    # Organization
    "OrganizationCreate", "OrganizationUpdate", "OrganizationResponse",
    "OrganizationStats", "OrganizationWithStatsResponse",
    "OrganizationMemberCreate", "OrganizationMemberInvite", "OrganizationMemberUpdate",
    "OrganizationMemberResponse", "OrganizationListResponse", "OrganizationMemberListResponse",
    
    # Agent
    "ModelProvider", "MessageRole",
    "AgentCreate", "AgentUpdate", "AgentResponse", "AgentRunRequest", "AgentRunResponse",
    "AgentSessionCreate", "AgentSessionResponse", "SessionMessageCreate", "SessionMessageResponse",
    "AgentListResponse", "AgentSessionListResponse", "SessionMessageListResponse",
    
    # Task
    "TaskType", "TaskStatus", "TaskCreate", "TaskUpdate", "TaskSchedule", "TaskResponse",
    "TaskStats", "TaskListResponse",
    
    # Billing
    "InvoiceStatus", "InvoiceResponse", "LineItemResponse", "InvoiceWithLineItemsResponse",
    "PaymentIntentCreate", "PaymentMethodResponse", "SubscriptionCreate", "SubscriptionResponse",
    "CreditPurchaseCreate", "CreditBalanceResponse", "InvoiceListResponse", "PaymentMethodListResponse",
    
    # Usage
    "UsageMetric", "UsageRecordResponse", "UsageQueryParams", "UsageStatsResponse",
    "UsageExportRequest", "UsageAlertCreate", "UsageAlertResponse", "UsageListResponse",
    
    # Admin
    "AdminUserUpdate", "AdminOrganizationUpdate", "SystemStatsResponse",
    "AuditLogQueryParams", "AuditLogEntryResponse", "AdminBillingAdjustment",
    "AdminBillingAdjustmentResponse", "AdminJobCreate", "AdminJobResponse",
    "AuditLogListResponse",
]