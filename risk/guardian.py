"""Retrain Guardian Agent — autonomous model lifecycle management.

Monitors system health, decides when to retrain the fraud model,
evaluates the result, and rolls back if quality degrades.

Architecture:
- Primary: Ollama LLM for reasoning about retrain/eval decisions
- Fallback: Deterministic rules (always available, no LLM dependency)
- Safety: asyncio.Lock prevents concurrent retrains, safe rollback via rename
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Awaitable, Callable
from uuid import uuid4

import httpx

from config import get_settings
from risk.trainer import MODEL_DIR, get_model_version

logger = logging.getLogger("fraud-agent.guardian")

# --- Concurrency guard ---
_retrain_lock = asyncio.Lock()

# --- Failure tracking ---
_consecutive_failures = 0
_FAILURE_BACKOFF_THRESHOLD = 3
_FAILURE_BACKOFF_SECONDS = 300  # 5 minutes

# --- LLM Prompts ---
GUARDIAN_PROMPT = """You are the Retrain Guardian for an autonomous fraud detection system.
Your job: decide whether the model should be retrained NOW based on system state.

SYSTEM STATE:
- Labels since last retrain: {labels_since}
- Total analyst labels: {total_labels}
- Transactions since last retrain: {txns_since_retrain}
- Current model version: {model_version}
- Current model F1: {current_f1}
- Current model precision: {current_precision}
- Score drift (recent vs older): {drift:.4f}
- Minutes since last retrain: {minutes_since_retrain:.1f}

RULES:
- If fewer than 20 total labels exist, training data is insufficient — SKIP.
- If 5+ new labels accumulated since last retrain, retraining is warranted.
- If score drift > 0.05 with 50+ transactions, the model may be stale.
- If 200+ transactions processed and >5 min since last retrain, consider staleness.

Respond in EXACTLY this format:
DECISION: RETRAIN or SKIP
REASONING: [1-2 sentences explaining why]
CONFIDENCE: HIGH or MEDIUM or LOW
"""

EVAL_PROMPT = """You are the Model Evaluator for an autonomous fraud detection system.
Compare the old model vs the newly trained model and decide: KEEP or ROLLBACK.

OLD MODEL: {old_version}
- Precision: {old_precision}
- Recall: {old_recall}
- F1: {old_f1}

NEW MODEL: {new_version}
- Precision: {new_precision}
- Recall: {new_recall}
- F1: {new_f1}

RULES:
- If F1 dropped by more than 10%, ROLLBACK.
- If precision dropped by more than 15%, ROLLBACK (false positives hurt trust).
- Otherwise, KEEP the new model.

Respond in EXACTLY this format:
DECISION: KEEP or ROLLBACK
REASONING: [1-2 sentences explaining why]
"""


# =============================================================================
# Context Gathering
# =============================================================================

async def _gather_context(db) -> dict[str, Any]:
    """Query DB for guardian decision context."""
    # Last retrain timestamp
    cursor = await db.execute(
        """SELECT MAX(timestamp) FROM metric_snapshots"""
    )
    row = await cursor.fetchone()
    last_retrain_ts = row[0] if row and row[0] else None

    # Labels since last retrain
    if last_retrain_ts:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM analyst_labels WHERE labeled_at > ?",
            (last_retrain_ts,),
        )
    else:
        cursor = await db.execute("SELECT COUNT(*) FROM analyst_labels")
    labels_since = (await cursor.fetchone())[0]

    # Total labels
    cursor = await db.execute("SELECT COUNT(*) FROM analyst_labels")
    total_labels = (await cursor.fetchone())[0]

    # Transactions since last retrain
    if last_retrain_ts:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM transactions WHERE timestamp > ?",
            (last_retrain_ts,),
        )
    else:
        cursor = await db.execute("SELECT COUNT(*) FROM transactions")
    txns_since_retrain = (await cursor.fetchone())[0]

    # Score drift: compare avg risk_score of recent 50 vs older 50
    cursor = await db.execute(
        """SELECT COALESCE(AVG(risk_score), 0.5) FROM (
            SELECT risk_score FROM risk_results ORDER BY timestamp DESC LIMIT 50
        )"""
    )
    recent_avg = (await cursor.fetchone())[0]

    cursor = await db.execute(
        """SELECT COALESCE(AVG(risk_score), 0.5) FROM (
            SELECT risk_score FROM risk_results ORDER BY timestamp DESC LIMIT 50 OFFSET 50
        )"""
    )
    older_avg = (await cursor.fetchone())[0]

    drift = abs(recent_avg - older_avg)

    # Current model version + metrics
    model_version = get_model_version()
    current_metrics = {"precision": None, "recall": None, "f1": None}
    metrics_file = MODEL_DIR / f"metrics_{model_version}.json"
    if metrics_file.exists():
        try:
            with open(metrics_file) as f:
                current_metrics = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # Time since last retrain
    minutes_since_retrain = 999.0
    if last_retrain_ts:
        try:
            last_dt = datetime.fromisoformat(last_retrain_ts)
            minutes_since_retrain = (
                datetime.utcnow() - last_dt
            ).total_seconds() / 60.0
        except (ValueError, TypeError):
            pass

    return {
        "labels_since": labels_since,
        "total_labels": total_labels,
        "txns_since_retrain": txns_since_retrain,
        "drift": drift,
        "recent_avg_score": recent_avg,
        "older_avg_score": older_avg,
        "model_version": model_version,
        "current_f1": current_metrics.get("f1"),
        "current_precision": current_metrics.get("precision"),
        "current_recall": current_metrics.get("recall"),
        "minutes_since_retrain": minutes_since_retrain,
        "last_retrain_ts": last_retrain_ts,
    }


# =============================================================================
# Deterministic Decision Logic (fallback, always available)
# =============================================================================

def _deterministic_decision(ctx: dict) -> tuple[str, str, str]:
    """Pure-function fallback: returns (decision, reasoning, confidence).

    decision: 'RETRAIN' or 'SKIP'
    """
    settings = get_settings()
    min_labels = settings.GUARDIAN_MIN_LABELS

    total = ctx.get("total_labels", 0)
    since = ctx.get("labels_since", 0)
    drift = ctx.get("drift", 0.0)
    txns = ctx.get("txns_since_retrain", 0)
    mins = ctx.get("minutes_since_retrain", 0.0)

    if total < 20:
        return "SKIP", f"Only {total} total labels — need 20+ for training", "HIGH"

    if since >= min_labels:
        return "RETRAIN", f"{since} new labels since last retrain (threshold: {min_labels})", "HIGH"

    if drift > 0.05 and txns > 50:
        return "RETRAIN", f"Score drift {drift:.3f} with {txns} transactions indicates model staleness", "MEDIUM"

    if txns > 200 and mins > 5:
        return "RETRAIN", f"{txns} transactions and {mins:.0f}min since last retrain — staleness check", "LOW"

    return "SKIP", f"{since} labels, drift {drift:.3f} — no retrain conditions met", "HIGH"


def _deterministic_eval(
    old_metrics: dict, new_metrics: dict
) -> tuple[str, str]:
    """Pure-function fallback: returns (decision, reasoning).

    decision: 'KEEP' or 'ROLLBACK'
    """
    old_f1 = old_metrics.get("f1") or 0
    new_f1 = new_metrics.get("f1") or 0
    old_prec = old_metrics.get("precision") or 0
    new_prec = new_metrics.get("precision") or 0

    if old_f1 > 0 and new_f1 < old_f1 * 0.9:
        return "ROLLBACK", f"F1 dropped from {old_f1:.3f} to {new_f1:.3f} (>{10}% decline)"

    if old_prec > 0 and new_prec < old_prec * 0.85:
        return "ROLLBACK", f"Precision dropped from {old_prec:.3f} to {new_prec:.3f} (>{15}% decline)"

    return "KEEP", f"New model acceptable: F1 {new_f1:.3f} (was {old_f1:.3f}), precision {new_prec:.3f}"


# =============================================================================
# Rollback — safe: rename, don't delete
# =============================================================================

def _rollback_model(new_version: str) -> bool:
    """Roll back a model version by renaming its files.

    Returns True if rollback was performed, False if only one model exists.
    """
    models = sorted(MODEL_DIR.glob("model_v*.joblib"))
    if len(models) <= 1:
        logger.warning("Cannot rollback — only one model exists")
        return False

    model_file = MODEL_DIR / f"model_{new_version}.joblib"
    metrics_file = MODEL_DIR / f"metrics_{new_version}.json"

    if model_file.exists():
        rolled = model_file.with_suffix(".joblib.rolled_back")
        model_file.rename(rolled)
        logger.info(f"Rolled back model: {model_file.name} -> {rolled.name}")

    if metrics_file.exists():
        rolled = metrics_file.with_suffix(".json.rolled_back")
        metrics_file.rename(rolled)
        logger.info(f"Rolled back metrics: {metrics_file.name} -> {rolled.name}")

    return True


# =============================================================================
# LLM Interaction
# =============================================================================

def _parse_guardian_response(text: str) -> tuple[str, str, str]:
    """Parse LLM output for retrain decision. Returns (decision, reasoning, confidence)."""
    decision = "SKIP"
    reasoning = ""
    confidence = "LOW"

    for line in text.strip().split("\n"):
        upper = line.strip().upper()
        if upper.startswith("DECISION:"):
            val = line.split(":", 1)[1].strip().upper()
            if "RETRAIN" in val:
                decision = "RETRAIN"
            else:
                decision = "SKIP"
        elif upper.startswith("REASONING:"):
            reasoning = line.split(":", 1)[1].strip()
        elif upper.startswith("CONFIDENCE:"):
            val = line.split(":", 1)[1].strip().upper()
            if "HIGH" in val:
                confidence = "HIGH"
            elif "MEDIUM" in val:
                confidence = "MEDIUM"
            else:
                confidence = "LOW"

    return decision, reasoning, confidence


def _parse_eval_response(text: str) -> tuple[str, str]:
    """Parse LLM output for eval decision. Returns (decision, reasoning)."""
    decision = "KEEP"
    reasoning = ""

    for line in text.strip().split("\n"):
        upper = line.strip().upper()
        if upper.startswith("DECISION:"):
            val = line.split(":", 1)[1].strip().upper()
            if "ROLLBACK" in val:
                decision = "ROLLBACK"
            else:
                decision = "KEEP"
        elif upper.startswith("REASONING:"):
            reasoning = line.split(":", 1)[1].strip()

    return decision, reasoning


def _call_guardian_llm(prompt: str) -> str | None:
    """Call Ollama for guardian decisions."""
    settings = get_settings()
    try:
        resp = httpx.post(
            f"{settings.OLLAMA_URL}/api/generate",
            json={
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 200},
            },
            timeout=settings.OLLAMA_TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json().get("response", "")
    except Exception as e:
        logger.debug(f"Guardian LLM call failed: {e}")
    return None


# =============================================================================
# Decision Logging
# =============================================================================

async def _log_decision(
    db,
    decision_type: str,
    reasoning: str,
    context: dict,
    outcome: str | None = None,
    model_version_before: str | None = None,
    model_version_after: str | None = None,
    source: str = "guardian",
) -> str:
    """Insert a row into agent_decisions. Returns decision_id."""
    decision_id = str(uuid4())
    await db.execute(
        """INSERT INTO agent_decisions
           (decision_id, timestamp, decision_type, reasoning, context,
            outcome, model_version_before, model_version_after, source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            decision_id,
            datetime.utcnow().isoformat(),
            decision_type,
            reasoning,
            json.dumps(context),
            outcome,
            model_version_before,
            model_version_after,
            source,
        ),
    )
    await db.commit()
    return decision_id


# =============================================================================
# Main Guardian Loop
# =============================================================================

async def run_guardian_loop(
    publish_fn: Callable[[dict], Any],
    retrain_fn: Callable[..., Awaitable[dict]],
):
    """Background loop: check system state, decide retrain, evaluate, rollback.

    Args:
        publish_fn: SSE publish function (_publish_event)
        retrain_fn: Shared retrain function (_do_retrain)
    """
    global _consecutive_failures
    settings = get_settings()

    # Initial delay — let system warm up
    logger.info("Guardian agent starting (60s warmup delay)")
    await asyncio.sleep(60)

    while True:
        try:
            interval = settings.GUARDIAN_CHECK_INTERVAL

            # Backoff on repeated failures
            if _consecutive_failures >= _FAILURE_BACKOFF_THRESHOLD:
                interval = _FAILURE_BACKOFF_SECONDS
                logger.warning(
                    f"Guardian backing off to {interval}s after "
                    f"{_consecutive_failures} consecutive failures"
                )

            await _guardian_tick(publish_fn, retrain_fn)
            _consecutive_failures = 0

        except asyncio.CancelledError:
            logger.info("Guardian agent shutting down")
            return
        except Exception as e:
            _consecutive_failures += 1
            logger.error(f"Guardian tick error ({_consecutive_failures}): {e}")

        # Sleep until next check
        try:
            interval = settings.GUARDIAN_CHECK_INTERVAL
            if _consecutive_failures >= _FAILURE_BACKOFF_THRESHOLD:
                interval = _FAILURE_BACKOFF_SECONDS
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("Guardian agent shutting down (during sleep)")
            return


async def _guardian_tick(
    publish_fn: Callable[[dict], Any],
    retrain_fn: Callable[..., Awaitable[dict]],
):
    """Single guardian check cycle."""
    from backend.db import get_db
    from risk.scorer import reload_model

    async with get_db() as db:
        ctx = await _gather_context(db)

    logger.debug(f"Guardian context: labels_since={ctx['labels_since']}, "
                 f"drift={ctx['drift']:.3f}, txns={ctx['txns_since_retrain']}")

    # --- Step 1: Decide whether to retrain ---
    source = "deterministic"
    llm_text = _call_guardian_llm(
        GUARDIAN_PROMPT.format(
            labels_since=ctx["labels_since"],
            total_labels=ctx["total_labels"],
            txns_since_retrain=ctx["txns_since_retrain"],
            model_version=ctx["model_version"],
            current_f1=ctx["current_f1"] or "N/A",
            current_precision=ctx["current_precision"] or "N/A",
            drift=ctx["drift"],
            minutes_since_retrain=ctx["minutes_since_retrain"],
        )
    )

    if llm_text:
        decision, reasoning, confidence = _parse_guardian_response(llm_text)
        source = "llm"
    else:
        decision, reasoning, confidence = _deterministic_decision(ctx)

    # --- Step 2: Handle SKIP (log to DB only, no SSE) ---
    if decision == "SKIP":
        async with get_db() as db:
            await _log_decision(
                db,
                decision_type="retrain_skipped",
                reasoning=reasoning,
                context=ctx,
                source=source,
                model_version_before=ctx["model_version"],
            )
        logger.debug(f"Guardian: SKIP — {reasoning}")
        return

    # --- Step 3: RETRAIN ---
    logger.info(f"Guardian: RETRAIN triggered — {reasoning}")
    old_version = ctx["model_version"]
    old_metrics = {
        "precision": ctx["current_precision"],
        "recall": ctx["current_recall"],
        "f1": ctx["current_f1"],
    }

    async with get_db() as db:
        await _log_decision(
            db,
            decision_type="retrain_triggered",
            reasoning=reasoning,
            context=ctx,
            source=source,
            model_version_before=old_version,
        )

    # Publish retrain triggered event
    publish_fn({
        "type": "agent_decision",
        "decision_type": "retrain_triggered",
        "reasoning": reasoning,
        "confidence": confidence,
        "source": source,
        "model_version": old_version,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Execute retrain (shared with endpoint, uses lock)
    async with _retrain_lock:
        retrain_result = await retrain_fn(write_snapshot=False)

    if not retrain_result.get("trained"):
        logger.warning(f"Guardian retrain failed: {retrain_result.get('error', 'unknown')}")
        return

    new_version = retrain_result["version"]
    new_metrics = retrain_result.get("metrics", {})

    # --- Step 4: Evaluate new model ---
    eval_source = "deterministic"
    eval_llm_text = _call_guardian_llm(
        EVAL_PROMPT.format(
            old_version=old_version,
            old_precision=old_metrics.get("precision") or "N/A",
            old_recall=old_metrics.get("recall") or "N/A",
            old_f1=old_metrics.get("f1") or "N/A",
            new_version=new_version,
            new_precision=new_metrics.get("precision", "N/A"),
            new_recall=new_metrics.get("recall", "N/A"),
            new_f1=new_metrics.get("f1", "N/A"),
        )
    )

    if eval_llm_text:
        eval_decision, eval_reasoning = _parse_eval_response(eval_llm_text)
        eval_source = "llm"
    else:
        eval_decision, eval_reasoning = _deterministic_eval(old_metrics, new_metrics)

    # --- Step 5: KEEP or ROLLBACK ---
    if eval_decision == "KEEP":
        reload_model()

        # Write metric snapshot now (guardian writes only after KEEP)
        async with get_db() as db:
            snapshot_id = str(uuid4())
            await db.execute(
                """INSERT INTO metric_snapshots (snapshot_id, timestamp, model_version, metrics)
                   VALUES (?, ?, ?, ?)""",
                (snapshot_id, datetime.utcnow().isoformat(), new_version,
                 json.dumps(new_metrics)),
            )
            await _log_decision(
                db,
                decision_type="model_kept",
                reasoning=eval_reasoning,
                context={"old": old_metrics, "new": new_metrics},
                outcome="kept",
                source=eval_source,
                model_version_before=old_version,
                model_version_after=new_version,
            )
            await db.commit()

        publish_fn({
            "type": "agent_decision",
            "decision_type": "model_kept",
            "reasoning": eval_reasoning,
            "confidence": confidence,
            "source": eval_source,
            "old_version": old_version,
            "new_version": new_version,
            "old_metrics": old_metrics,
            "new_metrics": new_metrics,
            "timestamp": datetime.utcnow().isoformat(),
        })
        logger.info(f"Guardian: KEPT {new_version} (F1: {new_metrics.get('f1', '?')})")

    else:
        # ROLLBACK
        rolled_back = _rollback_model(new_version)
        reload_model()

        async with get_db() as db:
            await _log_decision(
                db,
                decision_type="model_rolled_back",
                reasoning=eval_reasoning,
                context={"old": old_metrics, "new": new_metrics},
                outcome="rolled_back" if rolled_back else "kept_only_model",
                source=eval_source,
                model_version_before=old_version,
                model_version_after=old_version if rolled_back else new_version,
            )

        publish_fn({
            "type": "agent_decision",
            "decision_type": "model_rolled_back",
            "reasoning": eval_reasoning,
            "confidence": confidence,
            "source": eval_source,
            "old_version": old_version,
            "new_version": new_version,
            "old_metrics": old_metrics,
            "new_metrics": new_metrics,
            "timestamp": datetime.utcnow().isoformat(),
        })
        logger.info(
            f"Guardian: ROLLBACK {new_version} -> {old_version} — {eval_reasoning}"
        )
