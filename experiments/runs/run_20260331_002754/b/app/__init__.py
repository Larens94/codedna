"""AgentHub - AI Agent Marketplace SaaS Application.

Main application factory and initialization module.
"""

import os
import logging
from typing import Optional

from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from celery import Celery

# Initialize extensions (without app context)
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
bcrypt = Bcrypt()
mail = Mail()
celery = Celery()


def create_app(config_name: Optional[str] = None) -> Flask:
    """Create and configure the Flask application.
    
    Args:
        config_name: Configuration name (development, testing, production).
                   If None, uses FLASK_ENV environment variable.
                   
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    if config_name == 'production':
        from app.config import ProductionConfig
        app.config.from_object(ProductionConfig)
    elif config_name == 'testing':
        from app.config import TestingConfig
        app.config.from_object(TestingConfig)
    else:
        from app.config import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)
    
    # Override configuration from environment variables
    app.config.from_prefixed_env()
    
    # Configure logging
    configure_logging(app)
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    
    # Initialize Celery
    celery.conf.update(app.config)
    
    # Configure CORS
    CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}})
    
    # Register blueprints
    register_blueprints(app)
    
    # Register CLI commands
    register_commands(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register JWT callbacks
    register_jwt_callbacks()
    
    # Create uploads directory if it doesn't exist
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    
    # Import models to ensure they are registered with SQLAlchemy
    import_models()
    
    return app


def configure_logging(app: Flask) -> None:
    """Configure application logging.
    
    Args:
        app: Flask application instance
    """
    logging.basicConfig(
        level=app.config.get('LOG_LEVEL', 'INFO'),
        format=app.config.get('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    
    # Suppress noisy loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)


def register_blueprints(app: Flask) -> None:
    """Register all blueprints with the application.
    
    Args:
        app: Flask application instance
    """
    # Import blueprints here to avoid circular imports
    from app.api.health import health_bp
    from app.api.auth import auth_bp
    from app.api.users import users_bp
    from app.api.agents import agents_bp
    from app.api.marketplace import marketplace_bp
    from app.api.billing import billing_bp
    from app.api.tasks import tasks_bp
    from app.api.webhooks import webhooks_bp
    
    # Health check endpoints (no version prefix)
    app.register_blueprint(health_bp)
    
    # API v1 blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(users_bp, url_prefix='/api/v1/users')
    app.register_blueprint(agents_bp, url_prefix='/api/v1/agents')
    app.register_blueprint(marketplace_bp, url_prefix='/api/v1/marketplace')
    app.register_blueprint(billing_bp, url_prefix='/api/v1/billing')
    app.register_blueprint(tasks_bp, url_prefix='/api/v1/tasks')
    app.register_blueprint(webhooks_bp, url_prefix='/api/v1/webhooks')


def register_commands(app: Flask) -> None:
    """Register CLI commands.
    
    Args:
        app: Flask application instance
    """
    from app.commands import seed_db, create_admin, run_worker
    
    app.cli.add_command(seed_db)
    app.cli.add_command(create_admin)
    app.cli.add_command(run_worker)


def register_error_handlers(app: Flask) -> None:
    """Register global error handlers.
    
    Args:
        app: Flask application instance
    """
    @app.errorhandler(400)
    def bad_request(error):
        return {'error': 'Bad request', 'message': str(error.description) if hasattr(error, 'description') else str(error)}, 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return {'error': 'Unauthorized', 'message': 'Authentication required'}, 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return {'error': 'Forbidden', 'message': 'Insufficient permissions'}, 403
    
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Resource not found', 'message': str(error.description) if hasattr(error, 'description') else str(error)}, 404
    
    @app.errorhandler(422)
    def unprocessable_entity(error):
        return {'error': 'Unprocessable entity', 'message': str(error.description) if hasattr(error, 'description') else str(error)}, 422
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Internal server error: {error}')
        return {'error': 'Internal server error', 'message': 'An unexpected error occurred'}, 500


def register_jwt_callbacks() -> None:
    """Register JWT callbacks for token handling."""
    from flask_jwt_extended import get_jwt_identity
    
    @jwt.user_identity_loader
    def user_identity_lookup(user):
        return user.id if hasattr(user, 'id') else user
    
    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        from app.models.user import User
        identity = jwt_data["sub"]
        return User.query.filter_by(id=identity).one_or_none()
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_data):
        return {'error': 'Token has expired', 'message': 'Please refresh your token or login again'}, 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {'error': 'Invalid token', 'message': str(error)}, 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {'error': 'Authorization required', 'message': str(error)}, 401


def import_models() -> None:
    """Import all models to ensure they are registered with SQLAlchemy."""
    # This ensures SQLAlchemy knows about all models
    from app.models.user import User
    from app.models.agent import Agent, AgentVersion, AgentCategory, Tag
    from app.models.agent_run import AgentRun, AgentRunLog
    from app.models.subscription import Subscription, Plan, BillingAccount
    from app.models.credit import Credit
    from app.models.audit_log import AuditLog
    from app.models.organization import Organization
    from app.models.scheduled_task import ScheduledTask
    from app.models.usage_log import UsageLog
    from app.models.memory import Memory

# Create Celery application instance
def make_celery(app: Flask) -> Celery:
    """Create Celery application instance.
    
    Args:
        app: Flask application instance
        
    Returns:
        Celery application instance
    """
    celery_app = Celery(
        app.import_name,
        broker=app.config['CELERY_BROKER_URL'],
        backend=app.config['CELERY_RESULT_BACKEND']
    )
    
    celery_app.conf.update(app.config)
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery_app.Task = ContextTask
    return celery_app