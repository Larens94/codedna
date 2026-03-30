"""Authentication API endpoints for AgentHub."""

from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, 
    create_refresh_token, 
    jwt_required, 
    get_jwt_identity,
    get_jwt,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies
)
from sqlalchemy.exc import IntegrityError

from app import db, jwt, bcrypt
from app.models.user import User, UserSession
from app.schemas.auth import LoginSchema, RegisterSchema, RefreshSchema
from app.utils.validators import validate_schema

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user.
    
    Request body:
        email: User email
        username: Username
        password: Password
        first_name: Optional first name
        last_name: Optional last name
        
    Returns:
        User data and authentication tokens
    """
    data = validate_schema(RegisterSchema(), request.get_json())
    
    # Check if user already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already taken'}), 409
    
    # Create new user
    user = User(
        email=data['email'],
        username=data['username'],
        password=data['password'],
        first_name=data.get('first_name'),
        last_name=data.get('last_name')
    )
    
    # Create billing account for user
    from app.models.subscription import BillingAccount
    billing_account = BillingAccount(user=user)
    
    # Assign free plan
    from app.models.subscription import Plan, Subscription
    free_plan = Plan.query.filter_by(type='free').first()
    if free_plan:
        subscription = Subscription(
            user=user,
            plan=free_plan,
            status='active'
        )
    
    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Registration failed'}), 500
    
    # Create authentication tokens
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    
    # Create user session
    create_user_session(user.id, request, refresh_token)
    
    response = jsonify({
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token,
        'message': 'Registration successful'
    })
    
    # Set JWT cookies if configured
    if current_app.config.get('JWT_SET_COOKIES', False):
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
    
    return response, 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return tokens.
    
    Request body:
        email: User email
        password: Password
        
    Returns:
        User data and authentication tokens
    """
    data = validate_schema(LoginSchema(), request.get_json())
    
    # Find user by email
    user = User.query.filter_by(email=data['email']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Account is disabled'}), 403
    
    # Create authentication tokens
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    
    # Create user session
    create_user_session(user.id, request, refresh_token)
    
    response = jsonify({
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token,
        'message': 'Login successful'
    })
    
    # Set JWT cookies if configured
    if current_app.config.get('JWT_SET_COOKIES', False):
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
    
    return response


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token using refresh token.
    
    Returns:
        New access token
    """
    user_id = get_jwt_identity()
    
    # Verify user exists and is active
    user = User.query.get(user_id)
    if not user or not user.is_active:
        return jsonify({'error': 'User not found or inactive'}), 401
    
    # Create new access token
    access_token = create_access_token(identity=str(user.id))
    
    response = jsonify({
        'access_token': access_token,
        'message': 'Token refreshed'
    })
    
    # Set new access token cookie if configured
    if current_app.config.get('JWT_SET_COOKIES', False):
        set_access_cookies(response, access_token)
    
    return response


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user by invalidating tokens.
    
    Returns:
        Success message
    """
    # Get token and add to blacklist (if using blacklist)
    jti = get_jwt()['jti']
    
    # Remove user session
    user_id = get_jwt_identity()
    UserSession.query.filter_by(user_id=user_id).delete()
    
    response = jsonify({'message': 'Logged out successfully'})
    
    # Unset JWT cookies if configured
    if current_app.config.get('JWT_SET_COOKIES', False):
        unset_jwt_cookies(response)
    
    return response


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current authenticated user details.
    
    Returns:
        Current user data
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'user': user.to_dict(include_sensitive=True)})


@auth_bp.route('/sessions', methods=['GET'])
@jwt_required()
def get_user_sessions():
    """Get all active sessions for current user.
    
    Returns:
        List of active sessions
    """
    user_id = get_jwt_identity()
    sessions = UserSession.query.filter_by(user_id=user_id).all()
    
    session_list = []
    for session in sessions:
        session_list.append({
            'id': session.id,
            'user_agent': session.user_agent,
            'ip_address': session.ip_address,
            'created_at': session.created_at.isoformat() if session.created_at else None,
            'expires_at': session.expires_at.isoformat() if session.expires_at else None,
        })
    
    return jsonify({'sessions': session_list})


@auth_bp.route('/sessions/<int:session_id>', methods=['DELETE'])
@jwt_required()
def revoke_session(session_id: int):
    """Revoke a specific user session.
    
    Args:
        session_id: ID of session to revoke
        
    Returns:
        Success message
    """
    user_id = get_jwt_identity()
    session = UserSession.query.filter_by(id=session_id, user_id=user_id).first()
    
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    db.session.delete(session)
    db.session.commit()
    
    return jsonify({'message': 'Session revoked'})


def create_user_session(user_id: int, request, refresh_token: str) -> UserSession:
    """Create a new user session.
    
    Args:
        user_id: User ID
        request: Flask request object
        refresh_token: JWT refresh token
        
    Returns:
        Created UserSession object
    """
    # Calculate expiration (30 days for refresh token)
    expires_at = datetime.utcnow() + timedelta(days=30)
    
    session = UserSession(
        user_id=user_id,
        session_token=refresh_token,  # Using refresh token as session identifier
        refresh_token=refresh_token,
        user_agent=request.headers.get('User-Agent'),
        ip_address=request.remote_addr,
        expires_at=expires_at
    )
    
    db.session.add(session)
    db.session.commit()
    
    return session


@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    """Check if token is revoked.
    
    Args:
        jwt_header: JWT header
        jwt_payload: JWT payload
        
    Returns:
        True if token is revoked, False otherwise
    """
    # Implementation depends on token blacklist strategy
    # For simplicity, we're not implementing blacklist in this version
    return False


@jwt.user_identity_loader
def user_identity_lookup(user):
    """Create user identity for JWT.
    
    Args:
        user: User object or ID
        
    Returns:
        User ID as string
    """
    return str(user) if isinstance(user, (int, str)) else str(user.id)


@jwt.user_lookup_loader
def user_lookup_callback(jwt_header, jwt_payload):
    """Load user from JWT payload.
    
    Args:
        jwt_header: JWT header
        jwt_payload: JWT payload
        
    Returns:
        User object or None
    """
    identity = jwt_payload['sub']
    return User.query.get(identity)