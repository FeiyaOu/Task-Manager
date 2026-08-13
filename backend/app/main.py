"""FastAPI application (spec 05-api).

Loads the expertise cache from SQLite on startup, enables CORS for the local
frontend, and mounts the routers. Bind 0.0.0.0 is a run-time concern (run.sh).
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

import app.database as database
from app.config import get_settings
from app.routers import bugs, expertise, modules, repo, tasks
from app.services.expertise_cache import ExpertiseCache
from app.services.module_index import ModuleIndex


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database.create_db_and_tables()
        cache = ExpertiseCache()
        index = ModuleIndex()
        with Session(database.engine) as session:
            cache.load(session)
            index.build(session, module_depth=settings.module_depth)
        app.state.expertise_cache = cache
        app.state.module_index = index
        yield

    app = FastAPI(title="Task Manager", lifespan=lifespan)
    app.state.expertise_cache = ExpertiseCache()
    app.state.module_index = ModuleIndex()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for router in (bugs.router, tasks.router, modules.router, repo.router, expertise.router):
        app.include_router(router)
    return app


app = create_app()
