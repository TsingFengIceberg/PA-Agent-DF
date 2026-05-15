"""Collaboration HITL resume API — App layer.

The ONLY App-layer module allowed in Sprint 5. Provides:
- POST /api/threads/{id}/runs/{rid}/resume — Resume with stale check
- GET /api/threads/{id}/runs/{rid}/interrupt — Get interrupt status for UI

Stale check: Before resuming, reads the interrupt payload's _stale_check
timestamp and rejects if older than STALE_TIMEOUT_SECONDS.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["collaboration"])

# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

STALE_TIMEOUT_SECONDS = 30 * 60  # 30 minutes, must match hitl_gate.py

# ═══════════════════════════════════════════════════════════════════════════════
# Request / Response models
# ═══════════════════════════════════════════════════════════════════════════════


class ResumeRequest(BaseModel):
    """HITL resume request body."""

    resume: str = Field(
        ...,
        description="Human decision: 'approve', 'modify', or 'replan'",
        pattern=r"^(approve|modify|replan)$",
    )
    comment: str | None = Field(
        default=None,
        description="Optional human comment for audit trail",
    )


class ResumeResponse(BaseModel):
    """HITL resume response."""

    status: str = Field(..., description="'resumed' | 'stale' | 'error'")
    message: str = Field(default="", description="Human-readable status message")
    decision: str | None = Field(default=None, description="The decision that was applied")
    stale_seconds: int | None = Field(default=None, description="Seconds since approval was generated (if stale)")


class InterruptStatus(BaseModel):
    """Current interrupt status for UI rendering."""

    has_interrupt: bool = Field(..., description="Whether an interrupt is pending")
    payload: dict[str, Any] | None = Field(default=None, description="The interrupt payload (approval UI data)")
    stale: bool = Field(default=False, description="Whether the interrupt has exceeded timeout")
    elapsed_seconds: int | None = Field(default=None, description="Seconds since interrupt was generated")


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _check_stale(interrupt_payload: dict[str, Any]) -> tuple[bool, int]:
    """Check if the interrupt payload has gone stale.

    Returns:
        (is_stale: bool, elapsed_seconds: int)
    """
    stale_check = interrupt_payload.get("_stale_check", {})
    generated_at = stale_check.get("generated_at", 0)
    stale_after = stale_check.get("stale_after", STALE_TIMEOUT_SECONDS)

    elapsed = int(time.time() - generated_at)
    return elapsed > stale_after, elapsed


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/threads/{thread_id}/runs/{run_id}/interrupt", response_model=InterruptStatus)
async def get_interrupt_status(thread_id: str, run_id: str, request: Request) -> InterruptStatus:
    """Get the current interrupt status for the HITL approval UI.

    Returns the interrupt payload (approval options, summary, etc.) so the
    frontend can render the approval interface without hardcoding decisions.
    """
    try:
        # Get checkpointer from app state
        checkpointer = request.app.state.checkpointer if hasattr(request.app.state, "checkpointer") else None
        if checkpointer is None:
            return InterruptStatus(has_interrupt=False)

        # Read latest checkpoint for this thread
        config = {"configurable": {"thread_id": thread_id}}
        state = await checkpointer.aget(config)
        if state is None:
            return InterruptStatus(has_interrupt=False)

        # Check for interrupt in checkpoint metadata
        interrupts = state.get("__interrupt__", []) if isinstance(state, dict) else []
        if not interrupts:
            return InterruptStatus(has_interrupt=False)

        # Get the latest interrupt payload
        latest_interrupt = interrupts[-1] if isinstance(interrupts, list) else interrupts
        payload = latest_interrupt if isinstance(latest_interrupt, dict) else {"value": latest_interrupt}

        # Stale check
        is_stale, elapsed = _check_stale(payload)

        return InterruptStatus(
            has_interrupt=True,
            payload=payload,
            stale=is_stale,
            elapsed_seconds=elapsed,
        )
    except Exception:
        logger.exception("Failed to get interrupt status for thread=%s run=%s", thread_id, run_id)
        return InterruptStatus(has_interrupt=False)


@router.post("/threads/{thread_id}/runs/{run_id}/resume", response_model=ResumeResponse)
async def resume_hitl(thread_id: str, run_id: str, body: ResumeRequest, request: Request) -> ResumeResponse:
    """Resume a HITL-paused graph with the human's decision.

    Performs stale check before resuming. If the interrupt has expired
    (>30 minutes), rejects with a stale status rather than applying a
    potentially outdated decision.
    """
    decision = body.resume
    comment = body.comment

    logger.info("HITL resume: thread=%s run=%s decision=%s comment=%s", thread_id, run_id, decision, comment)

    try:
        checkpointer = request.app.state.checkpointer if hasattr(request.app.state, "checkpointer") else None
        if checkpointer is None:
            raise HTTPException(status_code=500, detail="Checkpointer not available")

        # Read checkpoint to verify interrupt exists and check staleness
        config = {"configurable": {"thread_id": thread_id}}
        state = await checkpointer.aget(config)

        if state is None:
            raise HTTPException(status_code=404, detail="No state found for this thread")

        interrupts = state.get("__interrupt__", []) if isinstance(state, dict) else []
        if not interrupts:
            raise HTTPException(status_code=409, detail="No interrupt pending for this thread")

        latest_interrupt = interrupts[-1] if isinstance(interrupts, list) else interrupts
        payload = latest_interrupt if isinstance(latest_interrupt, dict) else {}

        # Stale check
        is_stale, elapsed = _check_stale(payload)
        if is_stale:
            logger.warning("HITL: stale approval rejected for thread=%s (elapsed=%ds)", thread_id, elapsed)
            return ResumeResponse(
                status="stale",
                message=f"审批已过期（{elapsed // 60} 分钟前），请重新运行分析",
                decision=None,
                stale_seconds=elapsed,
            )

        # Resume via LangGraph — Command(resume=decision) triggers the interrupt() return
        from langgraph.types import Command

        resume_cmd = Command(resume=decision)

        # Get the compiled graph from app state
        graph = request.app.state.graph if hasattr(request.app.state, "graph") else None
        if graph is None:
            raise HTTPException(status_code=500, detail="Graph not available")

        # Stream the resume command to the graph
        resume_config = {**config, "configurable": {**config.get("configurable", {}), "run_id": run_id}}
        await graph.ainvoke(resume_cmd, resume_config)

        logger.info("HITL: resumed thread=%s with decision=%s", thread_id, decision)

        return ResumeResponse(
            status="resumed",
            message=f"已按 '{decision}' 恢复执行",
            decision=decision,
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to resume HITL for thread=%s run=%s", thread_id, run_id)
        raise HTTPException(status_code=500, detail="Failed to resume graph execution")
