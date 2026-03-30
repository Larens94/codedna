"""Health check endpoints for AgentHub."""

from datetime import datetime
from flask import Blueprint, jsonify, current_app
from sqlalchemy import text

from app import db

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Comprehensive health check endpoint.
    
    Returns:
        Health status of all critical services
    """
    health_status = {
        'status': 'healthy',
        'service': 'AgentHub API',
        'version': '1.0.0',
        'checks': {}
    }
    
    # Check database connectivity
    try:
        db.session.execute(text('SELECT 1'))
        health_status['checks']['database'] = {
            'status': 'healthy',
            'message': 'Database connection successful'
        }
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['checks']['database'] = {
            'status': 'unhealthy',
            'message': f'Database connection failed: {str(e)}'
        }
    
    # Check Redis connectivity (if configured for Celery)
    try:
        import redis
        from app.tasks import celery_app
        if celery_app.conf.broker_url:
            redis_client = redis.from_url(celery_app.conf.broker_url)
            redis_client.ping()
            health_status['checks']['redis'] = {
                'status': 'healthy',
                'message': 'Redis connection successful'
            }
    except Exception as e:
        health_status['checks']['redis'] = {
            'status': 'unhealthy',
            'message': f'Redis connection failed: {str(e)}'
        }
        # Don't mark overall as unhealthy for Redis unless critical
    
    # Check application configuration
    health_status['checks']['configuration'] = {
        'status': 'healthy',
        'message': 'Configuration loaded successfully',
        'environment': current_app.config.get('FLASK_ENV', 'unknown')
    }
    
    # Add timestamp
    health_status['timestamp'] = datetime.utcnow().isoformat()
    
    # Determine overall status code
    status_code = 200 if health_status['status'] == 'healthy' else 503
    
    return jsonify(health_status), status_code


@health_bp.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check for load balancers and orchestrators.
    
    Returns:
        Simple readiness status
    """
    try:
        # Check database
        db.session.execute(text('SELECT 1'))
        
        return jsonify({
            'status': 'ready',
            'service': 'AgentHub API',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'not_ready',
            'service': 'AgentHub API',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503


@health_bp.route('/live', methods=['GET'])
def liveness_check():
    """Liveness check for container orchestrators.
    
    Returns:
        Simple liveness status
    """
    return jsonify({
        'status': 'alive',
        'service': 'AgentHub API',
        'timestamp': datetime.utcnow().isoformat()
    }), 200