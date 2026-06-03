"""WebSocket live stream.

Pushes a compact platform snapshot to connected dashboards on a short interval —
instant updates without polling. Clients fall back to REST polling if the socket
is unavailable.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.clock import get_clock
from app.db.repository import get_repository
from app.models import IncidentStatus

router = APIRouter(tags=["stream"])
logger = logging.getLogger(__name__)


def build_snapshot() -> dict:
    repo = get_repository()
    incidents = repo.list_incidents()
    active = [i for i in incidents if i.status != IncidentStatus.resolved]
    preds = repo.list_predictions()
    return {
        "sim_time": get_clock().now(),
        "active_incidents": len(active),
        "top_prediction": (
            {
                "probability": preds[0].probability,
                "summary": preds[0].summary,
                "eta_seconds": preds[0].eta_seconds,
            }
            if preds
            else None
        ),
        "incidents": [
            {
                "id": i.id,
                "title": i.title,
                "status": i.status,
                "severity": i.severity,
                "probability": i.probability,
                "auto_remediated": i.auto_remediated,
            }
            for i in incidents[:20]
        ],
    }


@router.websocket("/ws/stream")
async def stream(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            await ws.send_json(build_snapshot())
            await asyncio.sleep(1.5)
    except WebSocketDisconnect:
        return
    except Exception as exc:  # noqa: BLE001
        logger.debug("stream socket closed: %s", exc)
