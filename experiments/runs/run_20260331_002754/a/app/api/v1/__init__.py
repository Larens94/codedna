"""app/api/v1/__init__.py — API version 1 package.

exports: api_router
used_by: app/api/__init__.py → api_router
rules:   all endpoints must include response models; must handle authentication via dependencies
agent:   Product Architect | 2024-03-30 | created API v1 structure
         message: "add API version header to all responses for future compatibility"
"""