"""FastAPI backend entry point."""
import asyncio
import json
import logging
import math
import time as _time_mod
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

import httpx
import numpy as np
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.db import get_db, init_db_tables
from config import get_settings
from patterns.features import compute_pattern_features
from patterns.miner import run_mining_job_async
from risk.explainer import _build_llm_prompt, _call_ollama_stream, explain_case
from risk.guardian import _retrain_lock, run_guardian_loop
from risk.scorer import THRESHOLDS, reload_model, score_transaction
from risk.trainer import (
    FEATURE_NAMES,
    MIN_SAMPLES_PER_CLASS,
    compute_training_features,
    get_model_version,
    train_model,
)

# --- Logging ---
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("fraud-agent")


# --- Pydantic Models (matching schemas) ---
class TransactionIn(BaseModel):
    amount: float = Field(ge=0, le=1_000_000_000)
    currency: str = Field(default="USD", max_length=10)
    sender_id: str = Field(max_length=512)
    receiver_id: str = Field(max_length=512)
    txn_type: str = Field(default="transfer", max_length=64)
    channel: str | None = Field(default="web", max_length=64)
    ip_address: str | None = Field(default=None, max_length=256)
    device_id: str | None = Field(default=None, max_length=256)
    is_fraud_ground_truth: bool | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("amount", mode="before")
    @classmethod
    def reject_special_floats(cls, v: Any) -> float:
        """Reject NaN, Infinity, and -Infinity before Pydantic coercion."""
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            raise ValueError("amount must be a finite number (not NaN or Infinity)")
        if isinstance(v, bool):
            raise ValueError("amount must be a number, not a boolean")
        return v


class TransactionOut(BaseModel):
    txn_id: str
    timestamp: str
    amount: float
    currency: str
    sender_id: str
    receiver_id: str
    txn_type: str
    channel: str | None
    risk_score: float | None = None
    decision: str | None = None


class CaseOut(BaseModel):
    case_id: str
    txn_id: str
    status: str
    created_at: str
    priority: str
    risk_score: float | None


class LabelIn(BaseModel):
    decision: Literal["fraud", "not_fraud", "needs_info"]
    confidence: str = "medium"  # low, medium, high
    labeled_by: str = Field(default="analyst_1", max_length=256)
    fraud_type: str | None = None
    notes: str | None = None


class MetricsOut(BaseModel):
    total_txns: int
    flagged_txns: int
    cases_open: int
    cases_closed: int
    precision: float | None
    recall: float | None
    f1: float | None = None
    model_version: str = "missing"


# --- Guardian globals ---
_guardian_task: asyncio.Task | None = None
_mining_task: asyncio.Task | None = None

# --- Auto-retrain debounce ---
_last_retrain_time: float = 0


# --- Periodic pattern mining ---
async def _periodic_mining(interval: int = 90):
    """Run pattern mining every `interval` seconds so the UI stays populated."""
    await asyncio.sleep(30)  # initial delay — let seed data land first
    while True:
        try:
            async with get_db() as db:
                patterns = await run_mining_job_async(db)
            for p in patterns:
                _publish_event({
                    "type": "pattern",
                    "name": p.name,
                    "pattern_type": p.pattern_type,
                    "confidence": p.confidence,
                    "timestamp": datetime.utcnow().isoformat(),
                })
            if patterns:
                logger.info("Periodic mining found %d patterns", len(patterns))
        except Exception:
            logger.exception("Periodic pattern mining error")
        await asyncio.sleep(interval)


# --- Auto-explain background task ---
async def _auto_explain_case(
    case_id: str,
    txn_id: str,
    txn_data: dict,
    risk_score: float,
    decision: str,
    features: dict,
    reasons: list[str],
    model_version: str,
):
    """Generate explanation in background and store it with the case.

    Runs as an asyncio task immediately after case creation so the
    explanation is ready before the analyst opens the case.
    """
    try:
        # Fetch related patterns
        related_patterns = []
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT name, pattern_type, confidence, description "
                "FROM pattern_cards WHERE status = 'active' LIMIT 20"
            )
            all_patterns = [
                {"name": r[0], "pattern_type": r[1], "confidence": r[2], "description": r[3]}
                for r in await cursor.fetchall()
            ]
            sender = txn_data.get("sender_id", "")
            receiver = txn_data.get("receiver_id", "")
            related_patterns = [
                p for p in all_patterns
                if sender in (p.get("description") or "")
                or receiver in (p.get("description") or "")
            ]

        # Generate explanation (runs LLM or template in executor to not block)
        loop = asyncio.get_running_loop()
        explanation = await loop.run_in_executor(
            None,
            lambda: explain_case(
                txn=txn_data,
                risk_score=risk_score,
                decision=decision,
                features=features,
                reasons=reasons,
                patterns=related_patterns,
                model_version=model_version,
            ),
        )

        # Store explanation in DB
        explanation_json = json.dumps(explanation)
        async with get_db() as db:
            await db.execute(
                "UPDATE cases SET explanation = ? WHERE case_id = ?",
                (explanation_json, case_id),
            )
            await db.commit()

        # Publish SSE event so UI can show the explanation immediately
        _publish_event({
            "type": "case_explained",
            "case_id": case_id,
            "txn_id": txn_id,
            "agent": explanation.get("agent", "unknown"),
            "summary": explanation.get("summary", "")[:200],
            "recommendation": explanation.get("recommendation", "")[:200],
            "timestamp": datetime.utcnow().isoformat(),
        })

        logger.info(
            "Auto-explained case %s via %s",
            case_id[:8], explanation.get("agent", "?"),
        )
    except Exception:
        logger.exception("Auto-explain failed for case %s", case_id[:8])


# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db_tables()
    global _guardian_task, _mining_task
    if get_settings().GUARDIAN_ENABLED:
        _guardian_task = asyncio.create_task(
            run_guardian_loop(_publish_event, _do_retrain)
        )
    _mining_task = asyncio.create_task(_periodic_mining())
    yield
    if _mining_task:
        _mining_task.cancel()
        try:
            await asyncio.wait_for(_mining_task, timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
    if _guardian_task:
        _guardian_task.cancel()
        try:
            await asyncio.wait_for(_guardian_task, timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass


# --- App ---
app = FastAPI(
    title="Autonomous Fraud Agent API",
    description="Backend for autonomous fraud detection demo",
    version="0.1.0",
    lifespan=lifespan,
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Global Exception Handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Let FastAPI handle validation and HTTP errors natively (422, 404, etc.)
    if isinstance(exc, (RequestValidationError, StarletteHTTPException, HTTPException)):
        raise exc
    logger.error(f"Unhandled error: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


# --- Request Logging Middleware ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = datetime.utcnow()
    response = await call_next(request)
    elapsed = (datetime.utcnow() - start).total_seconds() * 1000
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({elapsed:.0f}ms)"
    )
    return response


# --- Health ---
@app.get("/health")
async def health():
    """Basic health check."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/ready")
async def readiness():
    """Readiness probe — checks DB connectivity and model status."""
    checks = {"db": False, "model": False}
    try:
        async with get_db() as db:
            cursor = await db.execute("SELECT 1")
            await cursor.fetchone()
            checks["db"] = True
    except Exception as e:
        logger.warning(f"DB readiness check failed: {e}")

    checks["model"] = get_model_version() != "missing"
    all_ready = all(checks.values())

    return {
        "status": "ready" if all_ready else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
        "model_version": get_model_version(),
    }


# --- Velocity Feature Helpers ---
async def _compute_velocity_features(db, sender_id: str, receiver_id: str,
                                     device_id: str | None = None, ip_address: str | None = None) -> dict:
    """Query DB for recent activity to compute velocity + abuse features.

    Consolidated from 11 serial queries down to 3-4 queries using
    conditional aggregation (CASE WHEN inside aggregate functions).
    """
    now = datetime.utcnow().isoformat()

    # Query 1 — Sender stats (replaces 5 separate queries)
    cursor = await db.execute(
        """SELECT
               COUNT(CASE WHEN timestamp >= datetime(?, '-1 hour') THEN 1 END),
               COUNT(CASE WHEN timestamp >= datetime(?, '-24 hours') THEN 1 END),
               COALESCE(SUM(CASE WHEN timestamp >= datetime(?, '-1 hour') THEN amount END), 0),
               MAX(timestamp)
           FROM transactions WHERE sender_id = ?""",
        (now, now, now, sender_id),
    )
    sender_row = await cursor.fetchone()
    txn_count_1h = sender_row[0]
    txn_count_24h = sender_row[1]
    amount_sum_1h = sender_row[2]
    last_ts = sender_row[3]

    # Unique receivers needs a separate query (COUNT(DISTINCT CASE WHEN ...) is
    # unreliable in SQLite — it counts non-NULL results of the CASE, not distinct values)
    cursor = await db.execute(
        """SELECT COUNT(DISTINCT receiver_id) FROM transactions
           WHERE sender_id = ? AND timestamp >= datetime(?, '-24 hours')""",
        (sender_id, now),
    )
    unique_receivers_24h = (await cursor.fetchone())[0]

    # Query 2 — Receiver stats (replaces 3 separate queries)
    cursor = await db.execute(
        """SELECT
               COUNT(CASE WHEN timestamp >= datetime(?, '-24 hours') THEN 1 END),
               COALESCE(SUM(CASE WHEN timestamp >= datetime(?, '-24 hours') THEN amount END), 0)
           FROM transactions WHERE receiver_id = ?""",
        (now, now, receiver_id),
    )
    receiver_row = await cursor.fetchone()
    receiver_txn_count_24h = receiver_row[0]
    receiver_amount_sum_24h = receiver_row[1]

    # Unique senders to receiver also needs a separate query for same reason
    cursor = await db.execute(
        """SELECT COUNT(DISTINCT sender_id) FROM transactions
           WHERE receiver_id = ? AND timestamp >= datetime(?, '-24 hours')""",
        (receiver_id, now),
    )
    receiver_unique_senders_24h = (await cursor.fetchone())[0]

    # Query 3 — First-time counterparty (with 90-day bound)
    cursor = await db.execute(
        """SELECT COUNT(*) FROM transactions
           WHERE sender_id = ? AND receiver_id = ?
           AND timestamp >= datetime(?, '-90 days')""",
        (sender_id, receiver_id, now),
    )
    prior_pair_count = (await cursor.fetchone())[0]
    first_time_counterparty = prior_pair_count == 0

    # Query 4 — Device/IP reuse (combined into one query when both present)
    device_reuse_count_24h = 0
    ip_reuse_count_24h = 0
    if device_id and ip_address:
        cursor = await db.execute(
            """SELECT
                   (SELECT COUNT(DISTINCT sender_id) FROM transactions
                    WHERE device_id = ? AND timestamp >= datetime(?, '-24 hours') AND sender_id != ?),
                   (SELECT COUNT(DISTINCT sender_id) FROM transactions
                    WHERE ip_address = ? AND timestamp >= datetime(?, '-24 hours') AND sender_id != ?)""",
            (device_id, now, sender_id, ip_address, now, sender_id),
        )
        reuse_row = await cursor.fetchone()
        device_reuse_count_24h = reuse_row[0]
        ip_reuse_count_24h = reuse_row[1]
    elif device_id:
        cursor = await db.execute(
            """SELECT COUNT(DISTINCT sender_id) FROM transactions
               WHERE device_id = ? AND timestamp >= datetime(?, '-24 hours') AND sender_id != ?""",
            (device_id, now, sender_id),
        )
        device_reuse_count_24h = (await cursor.fetchone())[0]
    elif ip_address:
        cursor = await db.execute(
            """SELECT COUNT(DISTINCT sender_id) FROM transactions
               WHERE ip_address = ? AND timestamp >= datetime(?, '-24 hours') AND sender_id != ?""",
            (ip_address, now, sender_id),
        )
        ip_reuse_count_24h = (await cursor.fetchone())[0]

    # Time since last transaction from sender (computed from MAX(timestamp) in query 1)
    if last_ts:
        try:
            last_dt = datetime.fromisoformat(last_ts)
            delta = (datetime.utcnow() - last_dt).total_seconds() / 60.0
            time_since_last = min(delta, 1440)  # cap at 24 hours
        except (ValueError, TypeError):
            time_since_last = 60  # default
    else:
        time_since_last = 60  # first transaction from this sender

    return {
        "sender_txn_count_1h": txn_count_1h,
        "sender_txn_count_24h": txn_count_24h,
        "sender_amount_sum_1h": amount_sum_1h,
        "sender_unique_receivers_24h": unique_receivers_24h,
        "time_since_last_txn_minutes": time_since_last,
        "receiver_txn_count_24h": receiver_txn_count_24h,
        "receiver_amount_sum_24h": receiver_amount_sum_24h,
        "receiver_unique_senders_24h": receiver_unique_senders_24h,
        "first_time_counterparty": first_time_counterparty,
        "device_reuse_count_24h": device_reuse_count_24h,
        "ip_reuse_count_24h": ip_reuse_count_24h,
    }


# --- Transactions ---
@app.post("/transactions", response_model=TransactionOut)
async def create_transaction(txn: TransactionIn):
    """Ingest a transaction and run risk scoring."""
    txn_id = str(uuid4())
    timestamp = datetime.utcnow().isoformat()

    async with get_db() as db:
        # 0. Compute velocity features from sender history
        velocity = await _compute_velocity_features(
            db,
            sender_id=txn.sender_id,
            receiver_id=txn.receiver_id,
            device_id=txn.device_id,
            ip_address=txn.ip_address,
        )

        # 0b. Compute pattern-derived features (feedback loop from graph mining)
        pattern_feats = await compute_pattern_features(
            db, sender_id=txn.sender_id, receiver_id=txn.receiver_id,
        )

        # Score the transaction (with velocity + pattern context)
        txn_dict = {
            "txn_id": txn_id,
            "amount": txn.amount,
            "currency": txn.currency,
            "sender_id": txn.sender_id,
            "receiver_id": txn.receiver_id,
            "txn_type": txn.txn_type,
            "channel": txn.channel,
            "ip_address": txn.ip_address,
            "device_id": txn.device_id,
            "metadata": txn.metadata,
            **velocity,
            **pattern_feats,
        }
        try:
            risk_result = score_transaction(txn_dict)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=503,
                detail=str(exc),
            ) from exc
        flagged = risk_result.decision != "approve"

        # 1. Store transaction
        await db.execute(
            """INSERT INTO transactions
               (txn_id, timestamp, amount, currency, sender_id, receiver_id, txn_type, channel, ip_address, device_id, is_fraud_ground_truth, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (txn_id, timestamp, txn.amount, txn.currency, txn.sender_id, txn.receiver_id,
             txn.txn_type, txn.channel, txn.ip_address, txn.device_id,
             1 if txn.is_fraud_ground_truth else 0 if txn.is_fraud_ground_truth is not None else None,
             json.dumps(txn.metadata) if txn.metadata else None),
        )

        # 2. Store risk result
        await db.execute(
            """INSERT INTO risk_results
               (txn_id, timestamp, risk_score, flagged, threshold_used, model_version, features, matched_patterns)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (txn_id, risk_result.computed_at, risk_result.score, 1 if flagged else 0,
             THRESHOLDS["review"], risk_result.model_version,
             json.dumps(risk_result.features) if risk_result.features else None,
             json.dumps(risk_result.reasons) if risk_result.reasons else None),
        )

        # 3. Auto-create case if flagged
        if flagged:
            case_id = str(uuid4())
            priority = "high" if risk_result.decision == "block" else "medium"
            await db.execute(
                """INSERT INTO cases
                   (case_id, txn_id, status, created_at, priority, risk_score)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (case_id, txn_id, "open", timestamp, priority, risk_result.score),
            )

        await db.commit()

    # Publish SSE event so Orbital Greenhouse UI receives it
    _publish_event({
        "type": "transaction",
        "txn_id": txn_id,
        "amount": txn.amount,
        "currency": txn.currency,
        "sender_id": txn.sender_id,
        "receiver_id": txn.receiver_id,
        "txn_type": txn.txn_type,
        "risk_score": risk_result.score,
        "decision": risk_result.decision,
        "is_fraud_ground_truth": txn.is_fraud_ground_truth,
        "fraud_type": (txn.metadata or {}).get("fraud_type"),
        "timestamp": timestamp,
    })

    if flagged:
        _publish_event({
            "type": "case_created",
            "case_id": case_id,
            "txn_id": txn_id,
            "risk_score": risk_result.score,
            "decision": risk_result.decision,
            "timestamp": timestamp,
        })

        # 4. Auto-explain in background (autonomous — no analyst action needed)
        txn_for_explain = {
            "txn_id": txn_id,
            "amount": txn.amount,
            "currency": txn.currency,
            "sender_id": txn.sender_id,
            "receiver_id": txn.receiver_id,
            "txn_type": txn.txn_type,
            "channel": txn.channel,
            "timestamp": timestamp,
            "metadata": txn.metadata,
        }
        asyncio.create_task(_auto_explain_case(
            case_id=case_id,
            txn_id=txn_id,
            txn_data=txn_for_explain,
            risk_score=risk_result.score,
            decision=risk_result.decision,
            features=risk_result.features or {},
            reasons=risk_result.reasons or [],
            model_version=risk_result.model_version or "missing",
        ))

    return TransactionOut(
        txn_id=txn_id,
        timestamp=timestamp,
        amount=txn.amount,
        currency=txn.currency,
        sender_id=txn.sender_id,
        receiver_id=txn.receiver_id,
        txn_type=txn.txn_type,
        channel=txn.channel,
        risk_score=risk_result.score,
        decision=risk_result.decision,
    )


@app.get("/transactions", response_model=list[TransactionOut])
async def list_transactions(limit: int = Query(default=50, ge=0, le=1000)):
    """List recent transactions with risk scores."""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT t.txn_id, t.timestamp, t.amount, t.currency, t.sender_id,
                      t.receiver_id, t.txn_type, t.channel, r.risk_score,
                      CASE WHEN r.flagged = 1 THEN
                          CASE WHEN r.risk_score >= ? THEN 'block' ELSE 'review' END
                      ELSE 'approve' END as decision
               FROM transactions t
               LEFT JOIN risk_results r ON t.txn_id = r.txn_id
               ORDER BY t.timestamp DESC LIMIT ?""",
            (THRESHOLDS["block"], limit),
        )
        rows = await cursor.fetchall()

    return [
        TransactionOut(
            txn_id=r[0], timestamp=r[1], amount=r[2], currency=r[3],
            sender_id=r[4], receiver_id=r[5], txn_type=r[6], channel=r[7],
            risk_score=r[8], decision=r[9],
        )
        for r in rows
    ]


# --- Cases ---
@app.get("/cases", response_model=list[CaseOut])
async def list_cases(status: Literal["open", "in_review", "closed"] | None = None, limit: int = Query(default=50, ge=1, le=1000)):
    """List cases, optionally filtered by status."""
    async with get_db() as db:
        if status:
            cursor = await db.execute(
                "SELECT case_id, txn_id, status, created_at, priority, risk_score FROM cases WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            )
        else:
            cursor = await db.execute(
                "SELECT case_id, txn_id, status, created_at, priority, risk_score FROM cases ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        rows = await cursor.fetchall()

    return [
        CaseOut(case_id=r[0], txn_id=r[1], status=r[2], created_at=r[3], priority=r[4], risk_score=r[5])
        for r in rows
    ]


@app.post("/cases/{case_id}/label")
async def label_case(case_id: str, label_in: LabelIn):
    """Analyst labels a case as fraud/legit."""
    async with get_db() as db:
        # Check case exists
        cursor = await db.execute("SELECT txn_id, status FROM cases WHERE case_id = ?", (case_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Case not found")

        txn_id, current_status = row
        if current_status == "closed":
            raise HTTPException(status_code=400, detail="Case already closed")

        # Insert label
        label_id = str(uuid4())
        labeled_at = datetime.utcnow().isoformat()
        new_status = "closed" if label_in.decision in ("fraud", "not_fraud") else "in_review"

        await db.execute(
            """INSERT INTO analyst_labels (label_id, case_id, txn_id, decision, labeled_at, labeled_by, confidence, fraud_type, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (label_id, case_id, txn_id, label_in.decision, labeled_at, label_in.labeled_by,
             label_in.confidence, label_in.fraud_type, label_in.notes),
        )

        # Update case status
        closed_at = labeled_at if new_status == "closed" else None
        await db.execute(
            "UPDATE cases SET status = ?, updated_at = ?, closed_at = ? WHERE case_id = ?",
            (new_status, labeled_at, closed_at, case_id),
        )
        await db.commit()

    _publish_event({
        "type": "case_labeled",
        "case_id": case_id,
        "txn_id": txn_id,
        "decision": label_in.decision,
        "new_status": new_status,
        "timestamp": labeled_at,
    })

    # Auto-retrain: check if we have enough labels and retrain in background
    if label_in.decision in ("fraud", "not_fraud"):
        async def _maybe_auto_retrain():
            global _last_retrain_time
            try:
                # Debounce: skip if less than 60s since last retrain
                if _time_mod.time() - _last_retrain_time < 60:
                    logger.debug("Auto-retrain debounced (< 60s since last)")
                    return

                async with get_db() as db2:
                    cursor = await db2.execute(
                        "SELECT COUNT(*) FROM analyst_labels WHERE decision = 'fraud'"
                    )
                    fraud_count = (await cursor.fetchone())[0]
                    cursor = await db2.execute(
                        "SELECT COUNT(*) FROM analyst_labels WHERE decision = 'not_fraud'"
                    )
                    legit_count = (await cursor.fetchone())[0]

                if fraud_count >= MIN_SAMPLES_PER_CLASS and legit_count >= MIN_SAMPLES_PER_CLASS:
                    async with _retrain_lock:
                        await _do_retrain(write_snapshot=True)
                    _last_retrain_time = _time_mod.time()
                    logger.info("Auto-retrain completed after label threshold reached")
            except Exception as e:
                logger.warning(f"Auto-retrain skipped: {e}")

        asyncio.create_task(_maybe_auto_retrain())

    return {"label_id": label_id, "case_id": case_id, "new_status": new_status}


@app.get("/cases/suggested")
async def suggested_cases(limit: int = Query(default=10, ge=0, le=1000)):
    """Return cases sorted by model uncertainty (active learning).

    The model identifies transactions where it's least confident
    (risk_score closest to 0.5) and suggests those for analyst
    review first. This is genuine autonomous behavior -- the system
    decides what to ask the human.
    """
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT c.case_id, c.txn_id, c.status, c.created_at, c.priority,
                      c.risk_score, ABS(c.risk_score - 0.5) as uncertainty
               FROM cases c
               WHERE c.status IN ('open', 'in_review')
               ORDER BY uncertainty ASC
               LIMIT ?""",
            (limit,),
        )
        rows = await cursor.fetchall()

    return [
        {
            "case_id": r[0], "txn_id": r[1], "status": r[2],
            "created_at": r[3], "priority": r[4], "risk_score": r[5],
            "uncertainty": round(r[6], 4),
        }
        for r in rows
    ]


@app.get("/cases/{case_id}/explain")
async def explain_case_endpoint(case_id: str):
    """Return the AI-generated explanation for a flagged case.

    Explanations are auto-generated when cases are created (autonomous).
    This endpoint returns the cached result instantly. If the background
    task hasn't finished yet, it falls back to on-demand generation.
    """
    async with get_db() as db:
        # Get case (including pre-computed explanation)
        cursor = await db.execute(
            "SELECT txn_id, risk_score, priority, explanation FROM cases WHERE case_id = ?",
            (case_id,),
        )
        case_row = await cursor.fetchone()
        if not case_row:
            raise HTTPException(status_code=404, detail="Case not found")

        txn_id, case_risk_score, priority, cached_explanation = case_row

        # Return cached explanation if available (instant response)
        if cached_explanation:
            try:
                explanation = json.loads(cached_explanation)
                return {"case_id": case_id, "txn_id": txn_id, **explanation}
            except (json.JSONDecodeError, TypeError):
                pass

        # Fallback: generate on-demand if background task hasn't completed yet
        cursor = await db.execute(
            """SELECT txn_id, amount, currency, sender_id, receiver_id,
                      txn_type, channel, timestamp, metadata
               FROM transactions WHERE txn_id = ?""",
            (txn_id,),
        )
        txn_row = await cursor.fetchone()
        if not txn_row:
            raise HTTPException(status_code=404, detail="Transaction not found")

        txn = {
            "txn_id": txn_row[0], "amount": txn_row[1], "currency": txn_row[2],
            "sender_id": txn_row[3], "receiver_id": txn_row[4],
            "txn_type": txn_row[5], "channel": txn_row[6], "timestamp": txn_row[7],
            "metadata": None,
        }
        if txn_row[8]:
            try:
                txn["metadata"] = json.loads(txn_row[8])
            except (json.JSONDecodeError, TypeError):
                pass

        cursor = await db.execute(
            "SELECT risk_score, features, matched_patterns, model_version FROM risk_results WHERE txn_id = ?",
            (txn_id,),
        )
        risk_row = await cursor.fetchone()

        risk_score = case_risk_score or 0
        features = {}
        reasons = []
        model_version = "missing"

        if risk_row:
            risk_score = risk_row[0] or risk_score
            if risk_row[1]:
                try:
                    features = json.loads(risk_row[1])
                except (json.JSONDecodeError, TypeError):
                    pass
            if risk_row[2]:
                try:
                    reasons = json.loads(risk_row[2])
                except (json.JSONDecodeError, TypeError):
                    pass
            model_version = risk_row[3] or model_version

        if risk_score >= THRESHOLDS["block"]:
            decision = "block"
        elif risk_score >= THRESHOLDS["review"]:
            decision = "review"
        else:
            decision = "approve"

        cursor = await db.execute(
            "SELECT name, pattern_type, confidence, description FROM pattern_cards WHERE status = 'active' LIMIT 20"
        )
        all_patterns = [
            {"name": r[0], "pattern_type": r[1], "confidence": r[2], "description": r[3]}
            for r in await cursor.fetchall()
        ]
        related_patterns = [
            p for p in all_patterns
            if txn["sender_id"] in (p.get("description") or "")
            or txn["receiver_id"] in (p.get("description") or "")
        ]

    explanation = explain_case(
        txn=txn,
        risk_score=risk_score,
        decision=decision,
        features=features,
        reasons=reasons,
        patterns=related_patterns,
        model_version=model_version,
    )

    return {
        "case_id": case_id,
        "txn_id": txn_id,
        **explanation,
    }


# --- Streaming Explanation (AgentCore-inspired pattern) ---
@app.get("/cases/{case_id}/explain-stream")
async def explain_case_stream(case_id: str):
    """Stream AI explanation token-by-token via SSE.

    Inspired by AgentCore Runtime's async streaming pattern.
    Falls back to non-streaming explain_case if Ollama streaming fails.
    """
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT txn_id, risk_score FROM cases WHERE case_id = ?", (case_id,),
        )
        case_row = await cursor.fetchone()
        if not case_row:
            raise HTTPException(status_code=404, detail="Case not found")

        txn_id, case_risk_score = case_row

        cursor = await db.execute(
            """SELECT amount, currency, sender_id, receiver_id, txn_type, channel
               FROM transactions WHERE txn_id = ?""",
            (txn_id,),
        )
        txn_row = await cursor.fetchone()
        if not txn_row:
            raise HTTPException(status_code=404, detail="Transaction not found")

        cursor = await db.execute(
            "SELECT features, matched_patterns, model_version FROM risk_results WHERE txn_id = ?",
            (txn_id,),
        )
        risk_row = await cursor.fetchone()

    features = {}
    reasons = []
    model_version = "missing"
    if risk_row:
        try:
            features = json.loads(risk_row[0]) if risk_row[0] else {}
        except (json.JSONDecodeError, TypeError):
            pass
        try:
            reasons = json.loads(risk_row[1]) if risk_row[1] else []
        except (json.JSONDecodeError, TypeError):
            pass
        model_version = risk_row[2] or model_version

    risk_score = case_risk_score or 0
    decision = "block" if risk_score >= THRESHOLDS["block"] else "review" if risk_score >= THRESHOLDS["review"] else "approve"

    txn = {
        "amount": txn_row[0], "currency": txn_row[1], "sender_id": txn_row[2],
        "receiver_id": txn_row[3], "txn_type": txn_row[4], "channel": txn_row[5],
    }

    # Fetch related patterns (same logic as non-streaming endpoint)
    related_patterns = []
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT name, pattern_type, confidence, description FROM pattern_cards WHERE status = 'active' LIMIT 20"
        )
        all_patterns = [
            {"name": r[0], "pattern_type": r[1], "confidence": r[2], "description": r[3]}
            for r in await cursor.fetchall()
        ]
        related_patterns = [
            p for p in all_patterns
            if txn["sender_id"] in (p.get("description") or "")
            or txn["receiver_id"] in (p.get("description") or "")
        ]

    prompt = _build_llm_prompt(txn, risk_score, decision, features, reasons, related_patterns, model_version)

    async def generate():
        # Use asyncio.Queue as bridge between sync Ollama iterator and async generator
        # for true chunk-by-chunk streaming (no materialization)
        queue: asyncio.Queue = asyncio.Queue()
        sentinel = object()

        def _stream_to_queue():
            try:
                for chunk, done in _call_ollama_stream(prompt):
                    queue.put_nowait((chunk, done))
            except Exception as e:
                queue.put_nowait((f"Error: {e}", True))
            finally:
                queue.put_nowait((sentinel, True))

        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, _stream_to_queue)

        while True:
            item = await asyncio.wait_for(queue.get(), timeout=60)
            chunk, done = item
            if chunk is sentinel:
                yield "data: [DONE]\n\n"
                break
            yield f"data: {json.dumps({'text': chunk, 'done': done})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# --- Metrics ---
@app.get("/metrics", response_model=MetricsOut)
async def get_metrics():
    """Get current system metrics with real precision/recall from labels."""
    async with get_db() as db:
        total = (await (await db.execute("SELECT COUNT(*) FROM transactions")).fetchone())[0]
        flagged = (await (await db.execute("SELECT COUNT(*) FROM risk_results WHERE flagged = 1")).fetchone())[0]
        cases_open = (await (await db.execute("SELECT COUNT(*) FROM cases WHERE status = 'open' OR status = 'in_review'")).fetchone())[0]
        cases_closed = (await (await db.execute("SELECT COUNT(*) FROM cases WHERE status = 'closed'")).fetchone())[0]

        # Compute real precision/recall from analyst labels vs risk_results
        # Single SQL query with conditional aggregation (O(1) memory)
        cursor = await db.execute(
            """SELECT
                   SUM(CASE WHEN al.decision = 'fraud' AND r.flagged = 1 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN al.decision = 'not_fraud' AND r.flagged = 1 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN al.decision = 'fraud' AND r.flagged = 0 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN al.decision = 'not_fraud' AND r.flagged = 0 THEN 1 ELSE 0 END),
                   COUNT(*)
               FROM analyst_labels al
               JOIN risk_results r ON al.txn_id = r.txn_id
               WHERE al.decision IN ('fraud', 'not_fraud')"""
        )
        metrics_row = await cursor.fetchone()

    precision = None
    recall = None
    f1 = None

    if metrics_row and metrics_row[4] > 0:
        tp = metrics_row[0] or 0
        fp = metrics_row[1] or 0
        fn = metrics_row[2] or 0
        # tn = metrics_row[3] or 0  # available if needed
        # total_labels = metrics_row[4]  # available if needed

        flagged_as_fraud = tp + fp
        true_fraud = tp + fn

        if flagged_as_fraud > 0:
            precision = round(tp / flagged_as_fraud, 4)
        if true_fraud > 0:
            recall = round(tp / true_fraud, 4)
        if precision is not None and recall is not None and (precision + recall) > 0:
            f1 = round(2 * precision * recall / (precision + recall), 4)

    return MetricsOut(
        total_txns=total,
        flagged_txns=flagged,
        cases_open=cases_open,
        cases_closed=cases_closed,
        precision=precision,
        recall=recall,
        f1=f1,
        model_version=get_model_version(),
    )


# --- Shared Retrain Helper ---
async def _do_retrain(write_snapshot: bool = True) -> dict:
    """Shared retrain logic used by both /retrain endpoint and guardian.

    Args:
        write_snapshot: If True, write metric snapshot and publish SSE event.
            Guardian passes False (writes snapshot only after eval KEEP).

    Returns:
        Training result dict.
    """
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT t.txn_id, t.amount, t.txn_type, t.channel, t.sender_id,
                      t.timestamp, al.decision,
                      r.features
               FROM analyst_labels al
               JOIN transactions t ON al.txn_id = t.txn_id
               LEFT JOIN risk_results r ON t.txn_id = r.txn_id
               WHERE al.decision IN ('fraud', 'not_fraud')"""
        )
        rows = await cursor.fetchall()

    if len(rows) < MIN_SAMPLES_PER_CLASS * 2:
        return {
            "trained": False,
            "error": f"Need at least {MIN_SAMPLES_PER_CLASS * 2} labeled samples, have {len(rows)}",
        }

    X_list = []
    y_list = []

    for row in rows:
        txn_id, amount, txn_type, channel, sender_id, ts, decision, features_json = row

        if features_json:
            try:
                stored_features = json.loads(features_json)
                feature_vec = [stored_features.get(name, 0.0) for name in FEATURE_NAMES]
            except (json.JSONDecodeError, KeyError):
                feat_dict = compute_training_features(amount, txn_type, channel)
                feature_vec = [feat_dict.get(name, 0.0) for name in FEATURE_NAMES]
        else:
            feat_dict = compute_training_features(amount, txn_type, channel)
            feature_vec = [feat_dict.get(name, 0.0) for name in FEATURE_NAMES]

        X_list.append(feature_vec)
        y_list.append(1 if decision == "fraud" else 0)

    X = np.array(X_list)
    y = np.array(y_list)

    result = train_model(X, y)

    if result.get("trained") and write_snapshot:
        reload_model()

        async with get_db() as db:
            snapshot_id = str(uuid4())
            await db.execute(
                """INSERT INTO metric_snapshots (snapshot_id, timestamp, model_version, metrics)
                   VALUES (?, ?, ?, ?)""",
                (snapshot_id, datetime.utcnow().isoformat(), result["version"],
                 json.dumps(result["metrics"])),
            )
            await db.commit()

        _publish_event({
            "type": "retrain",
            "model_version": result["version"],
            "metrics": result.get("metrics", {}),
            "timestamp": datetime.utcnow().isoformat(),
        })

    return result


# --- Retrain ---
@app.post("/retrain")
async def retrain_model():
    """Retrain the ML model using analyst-labeled data.

    Collects labeled transactions, computes features, trains a
    XGBClassifier (XGBoost), and updates the scoring model.
    Uses shared lock to prevent concurrent retrains with guardian.
    """
    async with _retrain_lock:
        return await _do_retrain(write_snapshot=True)


# Also expose ground-truth labeled transactions for training (from simulator)
@app.post("/retrain-from-ground-truth")
async def retrain_from_ground_truth():
    """Retrain using ground truth labels (is_fraud_ground_truth from simulator).

    Useful for demo: pre-populate with simulated data, then retrain.
    """
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT t.txn_id, t.amount, t.txn_type, t.channel, t.sender_id,
                      t.timestamp, t.is_fraud_ground_truth,
                      r.features
               FROM transactions t
               LEFT JOIN risk_results r ON t.txn_id = r.txn_id
               WHERE t.is_fraud_ground_truth IS NOT NULL"""
        )
        rows = await cursor.fetchall()

    if len(rows) < MIN_SAMPLES_PER_CLASS * 2:
        return {
            "trained": False,
            "error": f"Need at least {MIN_SAMPLES_PER_CLASS * 2} labeled samples, have {len(rows)}",
        }

    X_list = []
    y_list = []

    for row in rows:
        txn_id, amount, txn_type, channel, sender_id, ts, is_fraud, features_json = row

        if features_json:
            try:
                stored_features = json.loads(features_json)
                feature_vec = [stored_features.get(name, 0.0) for name in FEATURE_NAMES]
            except (json.JSONDecodeError, KeyError):
                feat_dict = compute_training_features(amount, txn_type, channel)
                feature_vec = [feat_dict.get(name, 0.0) for name in FEATURE_NAMES]
        else:
            feat_dict = compute_training_features(amount, txn_type, channel)
            feature_vec = [feat_dict.get(name, 0.0) for name in FEATURE_NAMES]

        X_list.append(feature_vec)
        y_list.append(1 if is_fraud else 0)

    X = np.array(X_list)
    y = np.array(y_list)

    result = train_model(X, y)

    if result.get("trained"):
        reload_model()

        async with get_db() as db:
            snapshot_id = str(uuid4())
            await db.execute(
                """INSERT INTO metric_snapshots (snapshot_id, timestamp, model_version, metrics)
                   VALUES (?, ?, ?, ?)""",
                (snapshot_id, datetime.utcnow().isoformat(), result["version"],
                 json.dumps(result["metrics"])),
            )
            await db.commit()

        _publish_event({
            "type": "retrain",
            "model_version": result["version"],
            "metrics": result.get("metrics", {}),
            "source": "ground_truth",
            "timestamp": datetime.utcnow().isoformat(),
        })

    return result


# --- Pattern Mining ---
@app.post("/mine-patterns")
async def trigger_mining():
    """Trigger pattern mining on recent transactions."""
    async with get_db() as db:
        patterns = await run_mining_job_async(db)

    for p in patterns:
        _publish_event({
            "type": "pattern",
            "name": p.name,
            "pattern_type": p.pattern_type,
            "confidence": p.confidence,
            "timestamp": datetime.utcnow().isoformat(),
        })

    return {
        "patterns_found": len(patterns),
        "patterns": [
            {"name": p.name, "type": p.pattern_type, "confidence": p.confidence}
            for p in patterns
        ],
    }


# --- Pattern Cards ---
@app.get("/metric-snapshots")
async def list_metric_snapshots(limit: int = Query(default=20, ge=0, le=1000)):
    """List metric snapshots (for trend charts)."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT snapshot_id, timestamp, model_version, metrics FROM metric_snapshots ORDER BY timestamp ASC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()

    results = []
    for r in rows:
        metrics = {}
        if r[3]:
            try:
                metrics = json.loads(r[3])
            except (json.JSONDecodeError, TypeError):
                pass
        results.append({
            "snapshot_id": r[0],
            "timestamp": r[1],
            "model_version": r[2],
            **metrics,
        })
    return results


@app.get("/patterns")
async def list_patterns(limit: int = Query(default=20, ge=0, le=1000)):
    """List discovered pattern cards."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT pattern_id, name, description, discovered_at, status, pattern_type, confidence FROM pattern_cards ORDER BY discovered_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()

    return [
        {"pattern_id": r[0], "name": r[1], "description": r[2], "discovered_at": r[3],
         "status": r[4], "pattern_type": r[5], "confidence": r[6]}
        for r in rows
    ]


# --- Transaction Detail (for UI popups) ---
@app.get("/transactions/{txn_id}")
async def get_transaction(txn_id: str):
    """Get full transaction detail including risk result and case info."""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT t.txn_id, t.timestamp, t.amount, t.currency, t.sender_id,
                      t.receiver_id, t.txn_type, t.channel, t.ip_address,
                      t.device_id, t.is_fraud_ground_truth, t.metadata,
                      r.risk_score, r.features, r.matched_patterns, r.model_version,
                      c.case_id, c.status as case_status, c.priority
               FROM transactions t
               LEFT JOIN risk_results r ON t.txn_id = r.txn_id
               LEFT JOIN cases c ON t.txn_id = c.txn_id
               WHERE t.txn_id = ?""",
            (txn_id,),
        )
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found")

    metadata = None
    if row[11]:
        try:
            metadata = json.loads(row[11])
        except (json.JSONDecodeError, TypeError):
            metadata = {"raw": row[11]}

    features = None
    if row[13]:
        try:
            features = json.loads(row[13])
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "txn_id": row[0], "timestamp": row[1], "amount": row[2],
        "currency": row[3], "sender_id": row[4], "receiver_id": row[5],
        "txn_type": row[6], "channel": row[7], "ip_address": row[8],
        "device_id": row[9], "is_fraud_ground_truth": bool(row[10]) if row[10] is not None else None,
        "metadata": metadata,
        "risk_score": row[12], "features": features,
        "matched_patterns": row[14], "model_version": row[15],
        "case_id": row[16], "case_status": row[17], "priority": row[18],
    }


# --- SSE Event Stream (for Orbital Greenhouse UI) ---
# In-memory event bus for real-time UI updates
MAX_SUBSCRIBERS = 50
_event_subscribers: list[asyncio.Queue] = []


def _publish_event(event: dict):
    """Publish an event to all SSE subscribers."""
    for queue in _event_subscribers:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("SSE subscriber queue full, dropping event")


@app.get("/stream/events")
async def stream_events():
    """SSE endpoint for real-time system events.

    Events include:
    - transaction: new transaction scored
    - case_created: new case opened
    - case_labeled: analyst labeled a case
    - retrain: model retrained
    - pattern: new pattern discovered
    """
    if len(_event_subscribers) >= MAX_SUBSCRIBERS:
        raise HTTPException(
            status_code=503,
            detail=f"Too many SSE subscribers (max {MAX_SUBSCRIBERS})",
        )
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _event_subscribers.append(queue)

    async def generate():
        try:
            # Send initial heartbeat
            yield f"data: {json.dumps({'type': 'connected', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            try:
                _event_subscribers.remove(queue)
            except ValueError:
                pass

    return StreamingResponse(generate(), media_type="text/event-stream")


# --- Embedded Simulator Control (for Orbital Greenhouse UI) ---
_sim_task: asyncio.Task | None = None
_sim_config: dict = {
    "running": False,
    "tps": 1.0,
    "fraud_rate": 0.10,
    "fraud_types": {
        "structuring": True,
        "velocity_abuse": True,
        "wash_trading": True,
        "unauthorized_transfer": True,
        "bonus_abuse": True,
    },
}


class SimulatorConfig(BaseModel):
    tps: float = 1.0
    fraud_rate: float = 0.10
    fraud_types: dict[str, bool] | None = None


async def _run_embedded_simulator():
    """Run simulator in-process, publishing events to SSE stream."""
    import random

    from sim.main import (
        _FRAUD_GENERATORS,
        FRAUD_TYPES,
        generate_hero_transaction,
        generate_legit_transaction,
    )

    logger.info(f"Embedded simulator started: {_sim_config['tps']} TPS, {_sim_config['fraud_rate']*100:.0f}% fraud")
    count = 0

    async with httpx.AsyncClient() as client:
        while _sim_config["running"]:
            try:
                # Hero transaction every 25th
                if count > 0 and count % 25 == 0:
                    txn = generate_hero_transaction()
                    is_fraud = True
                    fraud_type = "wash_trading"
                else:
                    is_fraud = random.random() < _sim_config["fraud_rate"]
                    fraud_type = None

                    if is_fraud:
                        # Filter to enabled fraud types
                        enabled = [
                            ft for ft, enabled in _sim_config["fraud_types"].items()
                            if enabled
                        ]
                        if enabled:
                            # Use original weights for enabled types
                            weights = [FRAUD_TYPES.get(ft, 0.2) for ft in enabled]
                            fraud_type = random.choices(enabled, weights=weights, k=1)[0]
                            generator = _FRAUD_GENERATORS.get(fraud_type)
                            if generator:
                                txn = generator()
                            else:
                                txn = generate_legit_transaction()
                                is_fraud = False
                        else:
                            txn = generate_legit_transaction()
                            is_fraud = False
                    else:
                        txn = generate_legit_transaction()

                # Send to backend
                resp = await client.post(
                    f"http://127.0.0.1:{settings.BACKEND_PORT}/transactions",
                    json=txn, timeout=5,
                )
                if resp.status_code == 200:
                    # SSE events are now published by the POST /transactions
                    # endpoint itself, so no duplicate publish needed here.
                    pass

                count += 1
                await asyncio.sleep(1.0 / _sim_config["tps"])

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Simulator error: {e}")
                await asyncio.sleep(1.0)

    logger.info(f"Embedded simulator stopped after {count} transactions")


@app.get("/simulator/status")
async def simulator_status():
    """Get current simulator status and configuration."""
    return {
        "running": _sim_config["running"],
        "tps": _sim_config["tps"],
        "fraud_rate": _sim_config["fraud_rate"],
        "fraud_types": _sim_config["fraud_types"],
    }


@app.post("/simulator/start")
async def start_simulator(config: SimulatorConfig | None = None):
    """Start the embedded transaction simulator."""
    global _sim_task

    if _sim_config["running"]:
        return {"status": "already_running", **_sim_config}

    if config:
        _sim_config["tps"] = max(0.1, min(10.0, config.tps))
        _sim_config["fraud_rate"] = max(0.0, min(1.0, config.fraud_rate))
        if config.fraud_types:
            _sim_config["fraud_types"].update(config.fraud_types)

    _sim_config["running"] = True
    _sim_task = asyncio.create_task(_run_embedded_simulator())

    _publish_event({
        "type": "simulator_started",
        "config": {
            "tps": _sim_config["tps"],
            "fraud_rate": _sim_config["fraud_rate"],
            "fraud_types": _sim_config["fraud_types"],
        },
        "timestamp": datetime.utcnow().isoformat(),
    })

    return {"status": "started", **_sim_config}


@app.post("/simulator/stop")
async def stop_simulator():
    """Stop the embedded transaction simulator."""
    global _sim_task

    if not _sim_config["running"]:
        return {"status": "not_running"}

    _sim_config["running"] = False
    if _sim_task:
        _sim_task.cancel()
        try:
            await _sim_task
        except asyncio.CancelledError:
            pass
        _sim_task = None

    _publish_event({
        "type": "simulator_stopped",
        "timestamp": datetime.utcnow().isoformat(),
    })

    return {"status": "stopped"}


@app.post("/simulator/configure")
async def configure_simulator(config: SimulatorConfig):
    """Update simulator configuration (applies immediately if running)."""
    _sim_config["tps"] = max(0.1, min(10.0, config.tps))
    _sim_config["fraud_rate"] = max(0.0, min(1.0, config.fraud_rate))
    if config.fraud_types:
        _sim_config["fraud_types"].update(config.fraud_types)

    _publish_event({
        "type": "simulator_configured",
        "config": {
            "tps": _sim_config["tps"],
            "fraud_rate": _sim_config["fraud_rate"],
            "fraud_types": _sim_config["fraud_types"],
        },
        "timestamp": datetime.utcnow().isoformat(),
    })

    return {"status": "configured", **_sim_config}


# --- Guardian Agent Endpoints ---
@app.get("/guardian/status")
async def guardian_status():
    """Get current guardian agent status."""
    from risk.guardian import _consecutive_failures as guardian_failures

    return {
        "running": _guardian_task is not None and not _guardian_task.done(),
        "enabled": get_settings().GUARDIAN_ENABLED,
        "check_interval": get_settings().GUARDIAN_CHECK_INTERVAL,
        "consecutive_failures": guardian_failures,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/guardian/decisions")
async def list_guardian_decisions(limit: int = Query(default=20, ge=1, le=100)):
    """List recent guardian agent decisions."""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT decision_id, timestamp, decision_type, reasoning,
                      context, outcome, model_version_before,
                      model_version_after, source
               FROM agent_decisions
               ORDER BY timestamp DESC LIMIT ?""",
            (limit,),
        )
        rows = await cursor.fetchall()

    results = []
    for r in rows:
        ctx = {}
        if r[4]:
            try:
                ctx = json.loads(r[4])
            except (json.JSONDecodeError, TypeError):
                ctx = {"raw": r[4]}
        results.append({
            "decision_id": r[0],
            "timestamp": r[1],
            "decision_type": r[2],
            "reasoning": r[3],
            "context": ctx,
            "outcome": r[5],
            "model_version_before": r[6],
            "model_version_after": r[7],
            "source": r[8],
        })
    return results


@app.post("/guardian/start")
async def start_guardian():
    """Manually start the guardian agent."""
    global _guardian_task

    if _guardian_task and not _guardian_task.done():
        return {"status": "already_running"}

    _guardian_task = asyncio.create_task(
        run_guardian_loop(_publish_event, _do_retrain)
    )
    return {"status": "started", "timestamp": datetime.utcnow().isoformat()}


@app.post("/guardian/stop")
async def stop_guardian():
    """Manually stop the guardian agent."""
    global _guardian_task

    if not _guardian_task or _guardian_task.done():
        return {"status": "not_running"}

    _guardian_task.cancel()
    try:
        await asyncio.wait_for(_guardian_task, timeout=5.0)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass
    _guardian_task = None

    return {"status": "stopped", "timestamp": datetime.utcnow().isoformat()}
