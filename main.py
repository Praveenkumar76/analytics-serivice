import os
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, status
from pydantic import BaseModel
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("analytics-service")

app = FastAPI(title="Analytics Service", version="1.0.0")

NOTIFICATION_SERVICE_URL = os.getenv(
    "NOTIFICATION_SERVICE_URL",
    "http://notification-service.url-shortener-prod.svc.cluster.local"
).rstrip("/")

class EventRequest(BaseModel):
    event_type: str = "click"
    url_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

events_store: List[Dict[str, Any]] = []
# Milestones for triggering notification alert
MILESTONES = {1, 5, 10, 25, 50, 100, 250, 500, 1000}

@app.get("/healthz", status_code=status.HTTP_200_OK)
def healthz():
    return {"status": "ok", "service": "analytics-service"}

@app.get("/readyz", status_code=status.HTTP_200_OK)
def readyz():
    return {"status": "ready", "service": "analytics-service"}

@app.post("/api/v1/events", status_code=status.HTTP_201_CREATED)
async def record_event(event: EventRequest):
    record = {
        "id": len(events_store) + 1,
        "event_type": event.event_type,
        "url_id": event.url_id,
        "metadata": event.metadata or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    events_store.append(record)
    total_events = len(events_store)
    logger.info("Recorded event #%d: type=%s, url_id=%s", total_events, event.event_type, event.url_id)

    # Trigger notification if count reaches milestone
    if total_events in MILESTONES or (total_events > 0 and total_events % 100 == 0):
        alert_payload = {
            "service": "analytics-service",
            "event": "milestone_reached",
            "message": f"Traffic milestone reached: {total_events} total events recorded!",
            "total_events": total_events,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        target_url = f"{NOTIFICATION_SERVICE_URL}/api/v1/alerts"
        logger.info("Dispatching milestone alert to %s", target_url)
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.post(target_url, json=alert_payload)
                if resp.is_success:
                    logger.info("Notification successfully delivered (status: %d)", resp.status_code)
                else:
                    logger.warning("Notification service returned status %d: %s", resp.status_code, resp.text)
        except Exception as e:
            logger.warning("Could not reach notification-service: %s", str(e))

    return {
        "status": "success",
        "event_id": record["id"],
        "total_events": total_events,
        "event": record
    }

@app.get("/api/v1/stats", status_code=status.HTTP_200_OK)
def get_stats():
    total = len(events_store)
    clicks = sum(1 for e in events_store if e.get("event_type") == "click")
    views = sum(1 for e in events_store if e.get("event_type") == "view")
    other = total - clicks - views
    return {
        "total_events": total,
        "total_clicks": clicks,
        "total_views": views,
        "other_events": other,
        "recent_events": events_store[-10:] if events_store else [],
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
