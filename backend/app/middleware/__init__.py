"""Custom ASGI / FastAPI middleware.

Cross-cutting concerns beyond CORS: request IDs, timing, rate limits,
auth context propagation. Register in `app.main.create_application`.
"""
