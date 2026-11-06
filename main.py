import os

import psycopg
from fastapi import FastAPI, HTTPException
from psycopg.rows import dict_row

from schemas import DeviceCreate

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
    with connect(
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
