"""Authentication schemas for request validation."""

from marshmallow import Schema, fields, validate, ValidationError, validates_schema


class LoginSchema(Schema):
    """Schema for login requests."""
    
    email = fields.Email(required=True, description="User email address")
    password = fields.String(required=True, load_only=True, description="User password")


class RegisterSchema(Schema):
    """Schema for registration requests."""
    
    email = fields.Email(required=True, description="User email address")
    username = fields.String(
        required=True,
        validate=validate.Length(min=3, max=50),
        description="Username (3-50 characters)"
    )
    password = fields.String(
        required=True,
        load_only=True,
        validate=validate.Length(min=8),
        description="Password (minimum 8 characters)"
    )
    first_name = fields.String(
        validate=validate.Length(max=100),
        description="First name"
    )
    last_name = fields.String(
        validate=validate.Length(max=100),
        description="Last name"
    )


class RefreshSchema(Schema):
    """Schema for token refresh requests."""
    
    refresh_token = fields.String(required=True, description="Refresh token")


class ChangePasswordSchema(Schema):
    """Schema for password change requests."""
    
    current_password = fields.String(required=True, load_only=True, description="Current password")
    new_password = fields.String(
        required=True,
        load_only=True,
        validate=validate.Length(min=8),
        description="New password (minimum 8 characters)"
    )
    confirm_password = fields.String(required=True, load_only=True, description="Confirm new password")
    
    @validates_schema
    def validate_passwords(self, data, **kwargs):
        """Validate that new passwords match."""
        if data['new_password'] != data['confirm_password']:
            raise ValidationError('New passwords do not match', 'confirm_password')


class ResetPasswordRequestSchema(Schema):
    """Schema for password reset request."""
    
    email = fields.Email(required=True, description="User email address")


class ResetPasswordSchema(Schema):
    """Schema for password reset."""
    
    token = fields.String(required=True, description="Password reset token")
    new_password = fields.String(
        required=True,
        load_only=True,
        validate=validate.Length(min=8),
        description="New password (minimum 8 characters)"
    )
    confirm_password = fields.String(required=True, load_only=True, description="Confirm new password")
    
    @validates_schema
    def validate_passwords(self, data, **kwargs):
        """Validate that new passwords match."""
        if data['new_password'] != data['confirm_password']:
            raise ValidationError('New passwords do not match', 'confirm_password')


class UpdateProfileSchema(Schema):
    """Schema for profile update requests."""
    
    first_name = fields.String(
        validate=validate.Length(max=100),
        description="First name"
    )
    last_name = fields.String(
        validate=validate.Length(max=100),
        description="Last name"
    )
    avatar_url = fields.Url(
        allow_none=True,
        description="Avatar URL"
    )
    bio = fields.String(
        validate=validate.Length(max=500),
        description="Bio (maximum 500 characters)"
    )