import os
DB_URL = os.getenv("DB_URL", "sqlite:///app.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
