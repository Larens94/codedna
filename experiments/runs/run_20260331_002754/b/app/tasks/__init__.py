"""Celery tasks for AgentHub."""

import os
from celery import Celery
from flask import Flask

from app import create_app


def make_celery(app: Flask = None) -> Celery:
    """Create Celery application.
    
    Args:
        app: Flask application instance
        
    Returns:
        Celery application instance
    """
    app = app or create_app()
    
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    
    celery.conf.update(app.config)
    
    class ContextTask(celery.Task):
        """Celery task with Flask application context."""
        
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery


# Create Celery app instance
celery_app = make_celery()