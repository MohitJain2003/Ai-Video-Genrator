"""
WebSocket endpoint for real-time pipeline status updates.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.db.database import get_session
from app.models.job import Job

logger = logging.getLogger(__name__)

ws_router = APIRouter()

# Track connected clients per job
_connections: dict[str, list[WebSocket]] = {}


@ws_router.websocket("/api/v1/ws/{job_id}")
async def job_status_ws(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time job status updates.

    Clients connect to track processing progress.
    Server polls the database and pushes status changes.
    """
    await websocket.accept()
    logger.info(f"[WS] Client connected for job: {job_id}")

    # Register connection
    if job_id not in _connections:
        _connections[job_id] = []
    _connections[job_id].append(websocket)

    last_status = None

    try:
        while True:
            # Poll job status from database
            session = get_session()
            try:
                job = session.get(Job, job_id)
                if not job:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Job {job_id} not found",
                    })
                    break

                current_status = job.status.value

                # Send update if status changed
                if current_status != last_status:
                    await websocket.send_json({
                        "type": "status_update",
                        "job_id": job_id,
                        "status": current_status,
                        "overall_score": job.overall_score,
                        "retry_count": job.retry_count,
                        "error_message": job.error_message,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    last_status = current_status

                # Check for terminal states
                if current_status in ("completed", "completed_low_quality", "failed"):
                    await websocket.send_json({
                        "type": "pipeline_complete",
                        "job_id": job_id,
                        "status": current_status,
                        "overall_score": job.overall_score,
                        "output_path": job.output_path,
                        "error_message": job.error_message,
                    })
                    break

            finally:
                session.close()

            # Poll every 2 seconds
            await asyncio.sleep(2)

    except WebSocketDisconnect:
        logger.info(f"[WS] Client disconnected: {job_id}")
    except Exception as e:
        logger.error(f"[WS] Error for job {job_id}: {e}")
    finally:
        # Clean up connection
        if job_id in _connections:
            _connections[job_id] = [
                ws for ws in _connections[job_id] if ws != websocket
            ]
            if not _connections[job_id]:
                del _connections[job_id]


async def broadcast_status(job_id: str, status: str, message: str = ""):
    """Broadcast a status update to all connected clients for a job."""
    if job_id not in _connections:
        return

    data = {
        "type": "status_update",
        "job_id": job_id,
        "status": status,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    dead = []
    for ws in _connections[job_id]:
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)

    # Remove dead connections
    for ws in dead:
        _connections[job_id].remove(ws)
