"""Drop Studio API.

Run locally:  uvicorn app.main:app --reload
Docs:         http://localhost:8000/docs
"""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .auth import check_password, issue_token, require_auth
from .config import Settings, get_settings
from .db import SessionLocal
from .routers import brand, designs, drops, money, sales, stock, trends
from .schemas import LoginIn, TokenOut
from .services.ai import AIError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Drop Studio API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.frontend_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AIError)
    async def _ai_error(_: Request, exc: AIError):
        return JSONResponse({"detail": str(exc)}, status_code=exc.status)

    @app.get("/health", tags=["system"])
    def health():
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"ok": True}

    @app.get("/config", tags=["system"])
    def config(s: Settings = Depends(get_settings)):
        return {"auth_required": s.auth_enabled, "ai_enabled": s.ai_enabled, "model": s.anthropic_model}

    @app.post("/auth/login", response_model=TokenOut, tags=["system"])
    def login(body: LoginIn, s: Settings = Depends(get_settings)):
        if not s.auth_enabled:
            token, exp = issue_token(s)
            return TokenOut(token=token, expires_at=exp)
        if not check_password(body.password, s):
            raise HTTPException(401, "That password isn't right.")
        token, exp = issue_token(s)
        return TokenOut(token=token, expires_at=exp)

    protected = [Depends(require_auth)]
    for r in (brand.router, trends.router, drops.router, sales.router, money.router, stock.router, designs.router):
        app.include_router(r, dependencies=protected)
    return app


app = create_app()
