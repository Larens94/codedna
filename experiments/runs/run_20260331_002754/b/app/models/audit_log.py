"""Audit logging for system events and security monitoring."""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
import enum

from app import db


class AuditAction(enum.Enum):
    """Audit action enumeration."""
    
    # User actions
    USER_LOGIN = 'user_login'
    USER_LOGOUT = 'user_logout'
    USER_REGISTER = 'user_register'
    USER_UPDATE = 'user_update'
    USER_DELETE = 'user_delete'
    
    # Agent actions
    AGENT_CREATE = 'agent_create'
    AGENT_UPDATE = 'agent_update'
    AGENT_DELETE = 'agent_delete'
    AGENT_PUBLISH = 'agent_publish'
    AGENT_RUN = 'agent_run'
    
    # Billing actions
    SUBSCRIPTION_CREATE = 'subscription_create'
    SUBSCRIPTION_UPDATE = 'subscription_update'
    SUBSCRIPTION_CANCEL = 'subscription_cancel'
    INVOICE_CREATE = 'invoice_create'
    INVOICE_PAY = 'invoice_pay'
    CREDIT_ADD = 'credit_add'
    CREDIT_DEDUCT = 'credit_deduct'
    
    # Organization actions
    ORG_CREATE = 'org_create'
    ORG_UPDATE = 'org_update'
    ORG_DELETE = 'org_delete'
    ORG_MEMBER_ADD = 'org_member_add'
    ORG_MEMBER_REMOVE = 'org_member_remove'
    ORG_MEMBER_UPDATE = 'org_member_update'
    
    # System actions
    SETTINGS_UPDATE = 'settings_update'
    PLAN_UPDATE = 'plan_update'
    API_KEY_ROTATE = 'api_key_rotate'
    
    # Security actions
    PASSWORD_CHANGE = 'password_change'
    EMAIL_VERIFY = 'email_verify'
    TWO_FACTOR_ENABLE = 'two_factor_enable'
    TWO_FACTOR_DISABLE = 'two_factor_disable'


class AuditSeverity(enum.Enum):
    """Audit severity level."""
    
    INFO = 'info'
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class AuditLog(db.Model):
    """Audit log model for tracking system events.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to user (who performed action)
        organization_id: Foreign key to organization
        action: Audit action type
        severity: Severity level
        resource_type: Type of resource affected (e.g., 'user', 'agent', 'subscription')
        resource_id: ID of affected resource
        description: Human-readable description
        ip_address: IP address of request
        user_agent: User agent string
        metadata: Additional metadata (JSON)
        created_at: Creation timestamp
        user: Associated user
        organization: Associated organization
    """
    
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'))
    action = Column(Enum(AuditAction), nullable=False)
    severity = Column(Enum(AuditSeverity), default=AuditSeverity.INFO)
    resource_type = Column(String(50))
    resource_id = Column(Integer)
    description = Column(Text, nullable=False)
    ip_address = Column(String(45))  # IPv6 maximum length
    user_agent = Column(Text)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for efficient querying
    __table_args__ = (
        db.Index('ix_audit_logs_user_id_created_at', 'user_id', 'created_at'),
        db.Index('ix_audit_logs_organization_id_created_at', 'organization_id', 'created_at'),
        db.Index('ix_audit_logs_action_created_at', 'action', 'created_at'),
        db.Index('ix_audit_logs_resource', 'resource_type', 'resource_id'),
    )
    
    # Relationships
    user = relationship('User')
    organization = relationship('Organization')
    
    def get_metadata_dict(self) -> Dict[str, Any]:
        """Get metadata as dictionary.
        
        Returns:
            Metadata dictionary
        """
        return self.metadata or {}
    
    @classmethod
    def log(
        cls,
        action: AuditAction,
        description: str,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> 'AuditLog':
        """Create a new audit log entry.
        
        Args:
            action: Audit action type
            description: Human-readable description
            user_id: ID of user who performed action
            organization_id: Organization ID
            resource_type: Type of resource affected
            resource_id: ID of affected resource
            severity: Severity level
            ip_address: IP address of request
            user_agent: User agent string
            metadata: Additional metadata
            
        Returns:
            Created AuditLog instance
        """
        audit_log = cls(
            action=action,
            description=description,
            user_id=user_id,
            organization_id=organization_id,
            resource_type=resource_type,
            resource_id=resource_id,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
        )
        db.session.add(audit_log)
        db.session.commit()
        return audit_log
    
    def to_dict(self, include_user: bool = False) -> Dict[str, Any]:
        """Convert audit log to dictionary representation.
        
        Args:
            include_user: Whether to include user details
            
        Returns:
            Dictionary representation of audit log
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'organization_id': self.organization_id,
            'action': self.action.value if self.action else None,
            'severity': self.severity.value if self.severity else None,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'description': self.description,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'metadata': self.get_metadata_dict(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_user and self.user:
            data['user'] = self.user.to_dict()
        
        return data
    
    def __repr__(self) -> str:
        return f'<AuditLog {self.id}: {self.action.value} by User {self.user_id}>'