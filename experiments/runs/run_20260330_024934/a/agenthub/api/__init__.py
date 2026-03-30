"""__init__.py — API router package.

exports: agents, auth, billing, tasks, users
used_by: main.py
rules:   all routers must be imported here for main.py to use
agent:   BackendEngineer | 2024-01-15 | updated to include tasks router
         message: "verify all router modules follow consistent error handling patterns"
"""

# Import all routers for easy access from main.py
from agenthub.api import agents
from agenthub.api import auth
from agenthub.api import billing
from agenthub.api import tasks
from agenthub.api import users

__all__ = ["agents", "auth", "billing", "tasks", "users"]