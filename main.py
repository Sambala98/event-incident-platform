import os

import psycopg
from fastapi import FastAPI, HTTPException,Response
from psycopg.rows import dict_row

from fastapi import FastAPI, HTTPException, Response
from schemas import DeviceCreate, EventCreate,IncidentAcknowledge
from fastapi.responses import PlainTextResponse

app = FastAPI(title="Event Incident Platform")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

def connect_db():
    return psycopg.connect(
        host="127.0.0.1",
        port=5546,
        dbname="incident_db",
        user="incident_app",
        password=os.environ["POSTGRES_PASSWORD"],
        connect_timeout=5,
        row_factory=dict_row,
    )

@app.post("/devices", status_code=201)
def create_device(device: DeviceCreate) -> dict:
    with connect_db() as conn:
        row = conn.execute(
            """
            INSERT INTO public.devices (name, heartbeat_interval_seconds)
            VALUES (%s, %s)
            RETURNING id, name, heartbeat_interval_seconds
            """,
            (device.name, device.heartbeat_interval_seconds),
        ).fetchone()

        if row is None:
            raise RuntimeError("Device insert returned no row")

    return row
@app.get("/devices/{device_id}")
def get_device(device_id: int) -> dict:
    with connect_db() as conn:
        row = conn.execute(
            """
            SELECT id, name, heartbeat_interval_seconds
            FROM public.devices
            WHERE id = %s
            """,
            (device_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Device not found")

    return row
@app.post("/events", status_code=201)
def create_event(event: EventCreate, response: Response) -> dict:
    try:
        with connect_db() as conn:
            inserted = conn.execute(
                """
                INSERT INTO public.device_events
                    (event_id, device_id, event_type, occurred_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (event_id) DO NOTHING
                RETURNING event_id, device_id, event_type, occurred_at, received_at
                """,
                (event.event_id, event.device_id, event.event_type, event.occurred_at),
            ).fetchone()

            if inserted is not None:
                conn.execute(
                    "INSERT INTO public.event_outbox (event_id) VALUES (%s)",
                    (event.event_id,),
                )
                return inserted

            existing = conn.execute(
                """
                SELECT event_id, device_id, event_type, occurred_at, received_at
                FROM public.device_events
                WHERE event_id = %s
                """,
                (event.event_id,),
            ).fetchone()

            if existing is None:
                raise RuntimeError("Conflicting event could not be read")

            if (
                existing["device_id"] != event.device_id
                or existing["event_type"] != event.event_type
                or existing["occurred_at"] != event.occurred_at
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Event ID already exists with different data",
                )

            response.status_code = 200
            return existing
    except psycopg.errors.ForeignKeyViolation as exc:
        raise HTTPException(status_code=404, detail="Device not found") from exc

@app.post("/incidents/{incident_id}/acknowledge")
def acknowledge_incident(incident_id: int, request: IncidentAcknowledge) -> dict:
    with connect_db() as conn:
        audit_entry = conn.execute(
            """
            WITH acknowledged AS (
                UPDATE public.incidents
                SET acknowledged_by = %s,
                    acknowledged_at = CURRENT_TIMESTAMP
                WHERE id = %s
                  AND resolved_at IS NULL
                  AND acknowledged_at IS NULL
                RETURNING id, acknowledged_by, acknowledged_at
            )
            INSERT INTO public.incident_audit_log
                (incident_id, action, actor, created_at)
            SELECT id, 'acknowledged', acknowledged_by, acknowledged_at
            FROM acknowledged
            RETURNING incident_id, action, actor, created_at
            """,
            (request.actor, incident_id),
        ).fetchone()

        if audit_entry is None:
            incident = conn.execute(
                "SELECT id FROM public.incidents WHERE id = %s",
                (incident_id,),
            ).fetchone()
            if incident is None:
                raise HTTPException(status_code=404, detail="Incident not found")
            raise HTTPException(
                status_code=409,
                detail="Incident is already acknowledged or resolved",
            )

    return audit_entry

@app.post("/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: int, request: IncidentAcknowledge) -> dict:
    with connect_db() as conn:
        audit_entry = conn.execute(
            """
            WITH resolved AS (
                UPDATE public.incidents
                SET resolved_at = CURRENT_TIMESTAMP
                WHERE id = %s
                  AND resolved_at IS NULL
                RETURNING id, resolved_at
            )
            INSERT INTO public.incident_audit_log
                (incident_id, action, actor, created_at)
            SELECT id, 'resolved', %s, resolved_at
            FROM resolved
            RETURNING incident_id, action, actor, created_at
            """,
            (incident_id, request.actor),
        ).fetchone()

        if audit_entry is None:
            incident = conn.execute(
                "SELECT id FROM public.incidents WHERE id = %s",
                (incident_id,),
            ).fetchone()
            if incident is None:
                raise HTTPException(status_code=404, detail="Incident not found")
            raise HTTPException(
                status_code=409,
                detail="Incident is already resolved",
            )

    return audit_entry

@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    with connect_db() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS open_count
            FROM public.incidents
            WHERE resolved_at IS NULL
            """
        ).fetchone()

    return PlainTextResponse(
        "# HELP incidents_open Current number of open incidents.\n"
        "# TYPE incidents_open gauge\n"
        f"incidents_open {row['open_count']}\n",
        media_type="text/plain; version=0.0.4",
    )