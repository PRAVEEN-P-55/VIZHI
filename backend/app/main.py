"""FastAPI application entrypoint.

Wires routers, CORS, and startup: ensures the DB + demo users exist, loads the
trained ML pipeline, and auto-raises alerts for current high-risk forecasts.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import SessionLocal, init_db
from .auth import routes as auth_routes
from .routers import agent, alerts, complaints, features_extra, graph, outcomes, predict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vizhi")

app = FastAPI(
    title=settings.app_name,
    description="VIZHI predictive cash-withdrawal intelligence for I4C (SIH 26184).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(predict.router)
app.include_router(complaints.router)
app.include_router(alerts.router)
app.include_router(graph.router)
app.include_router(agent.router)
app.include_router(features_extra.router)
app.include_router(outcomes.router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "app": settings.app_name}


@app.on_event("startup")
def on_startup():
    init_db()
    # First-run bootstrap for local and container deployments.
    try:
        from .ingest import ingest_all
        from .models import Complaint

        db = SessionLocal()
        try:
            is_empty = db.query(Complaint).count() == 0
        finally:
            db.close()
        if is_empty:
            ingest_all(verbose=False)
            logger.info("startup: datasets ingested")
    except Exception as e:  # pragma: no cover
        logger.warning("dataset bootstrap skipped: %s", e)
    # ensure demo users exist
    try:
        from seed_users import seed

        seed(verbose=False)
    except Exception as e:  # pragma: no cover
        logger.warning("user seeding skipped: %s", e)

    # load pipeline + auto-raise alerts for high-risk forecasts
    try:
        from .ml.pipeline import get_pipeline
        from .alerts.dispatch import scan_and_raise

        pipe = get_pipeline()
        preds = pipe.get_predictions()["predictions"]
        db = SessionLocal()
        try:
            raised = scan_and_raise(db, preds)
            logger.info("startup: %d high-risk alerts raised", len(raised))
        finally:
            db.close()
    except FileNotFoundError:
        logger.warning("No trained artifacts found. Run `python train.py` first.")
    except Exception as e:  # pragma: no cover
        logger.warning("startup analytics skipped: %s", e)
