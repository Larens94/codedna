"""config.py -- Environment configuration loader.

Exports: DB_URL, SECRET_KEY
Used by: db/queries.py, auth/login.py

Rules:
  - Non hardcodare secrets. Usare variabili d'ambiente.
"""
import os
DB_URL = os.getenv("DB_URL", "sqlite:///app.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
