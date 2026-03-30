"""main.py — Application entry point for production.

exports: uvicorn server startup
used_by: Dockerfile → CMD, production deployment → process manager
rules:   must use uvicorn workers for production; config loaded from environment
agent:   Product Architect | 2024-03-30 | created production entry point
         message: "consider adding graceful shutdown handling for production"
"""

import uvicorn
from app.main import create_app

# Create FastAPI application
app = create_app()

if __name__ == "__main__":
    # Run with uvicorn programmatically
    # In production, use: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload in production
        workers=1,     # Set to number of CPU cores in production
        log_level="info",
        access_log=True,
    )