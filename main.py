import os

import psycopg
from fastapi import FastAPI
from psycopg.rows import dict_row

from schemas import DeviceCreate

app = FastAPI(title="Event Incident Platform")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/devices", status_code=201)
def create_device(device: DeviceCreate) -> dict:
    with psycopg.connect(
        host="127.0.0.1",
        port=5546,
        dbname="incident_db",
        user="incident_app",
        password=os.environ["POSTGRES_PASSWORD"],
        connect_timeout=5,
        row_factory=dict_row,
    ) as conn:
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