"""app/__init__.py — AgentHub application package.

exports: create_app(config: Config) -> FastAPI
used_by: main.py → application entry point
rules:   must support dependency injection for all services; config must be validated
agent:   Product Architect | 2024-03-30 | created application factory pattern
         message: "verify that all services can be initialized without circular dependencies"
"""