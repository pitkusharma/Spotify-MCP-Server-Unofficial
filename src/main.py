from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.common.exceptions import attach_exception_handlers
from src.core.config import settings
from src.routes.auth.auth_routes import router
from src.spotify_mcp.server import mcp
from src.spotify_mcp.tools.spotify_tools import *


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# 🚀 Mount router
app.include_router(router)

# Attach exception handlers

attach_exception_handlers(app)

# Mount MCP Server
app.mount("/mcp", mcp.sse_app())
