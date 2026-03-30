"""dependencies.py — Authentication dependencies for FastAPI.
"""dependencies.py — Authentication dependencies for FastAPI.

exports: get_current_user, get_current_active_user, get_current_superuser
used_by: all API routers
rules:   must validate JWT tokens; must check user status and permissions
agent:   FrontendDesigner | 2024-01-15 | updated to use new JWT module
         message: "implement proper JWT validation with token blacklist support"
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from agenthub.db.session import get_db
from agenthub.db.models import User
from agenthub.auth.jwt import get_current_user as jwt_get_current_user
from agenthub.auth.jwt import get_current_active_user as jwt_get_current_active_user
from agenthub.auth.jwt import get_current_superuser as jwt_get_current_superuser
from agenthub.auth.oauth2 import oauth2_scheme

# Re-export the functions from jwt.py
get_current_user = jwt_get_current_user
get_current_active_user = jwt_get_current_active_user
get_current_superuser = jwt_get_current_superuser
            detail="Superuser privileges required",
        )
    return current_user