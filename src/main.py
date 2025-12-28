from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from src.common.exceptions import attach_exception_handlers
from src.core.config import settings
from src.routes.auth.auth_routes import router
from src.spotify_mcp.server import mcp
from src.core.db import init_db, close_db
from src.spotify_mcp.tools.spotify_tools import *


# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- Startup ----
    await init_db()
    yield
    # ---- Shutdown ----
    await close_db()

# app
app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Allowed hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[host for host in settings.ALLOWED_HOSTS.split(",") if host],
)

# 🚀 Mount router
app.include_router(router)

# Attach exception handlers

attach_exception_handlers(app)

# Mount MCP Server
mcp_app = mcp.sse_app()

mcp_app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[host for host in settings.ALLOWED_HOSTS.split(",") if host],
)

app.mount("/mcp", mcp_app)

