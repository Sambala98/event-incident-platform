import json
from datetime import datetime
from uuid import UUID

import pika

from outbox_publisher import connect_db
def record_processed_event(conn, event_id):
    inserted = conn.execute(
        """
        INSERT INTO public.processed_device_events (event_id)
        VALUES (%s)
        ON CONFLICT (event_id) DO NOTHING
        RETURNING event_id
        """,
        (event_id,),
    ).fetchone()

    return inserted is not None
def update_last_heartbeat(conn, device_id, occurred_at):
    updated = conn.execute(
        """
        UPDATE public.devices
        SET last_heartbeat_at = %s
        WHERE id = %s
          AND (last_heartbeat_at IS NULL OR last_heartbeat_at < %s)
        RETURNING id
        """,
        (occurred_at, device_id, occurred_at),
    ).fetchone()

    return updated is not None


def process_device_event(conn, event_id, device_id, event_type, occurred_at):
    if not record_processed_event(conn, event_id):
        return "duplicate"

    if event_type == "heartbeat":
        update_last_heartbeat(conn, device_id, occurred_at)

    return "processed"
def consume_one_event():
    params = pika.ConnectionParameters(host="127.0.0.1", port=5672)
    connection = pika.BlockingConnection(params)

    try:
        channel = connection.channel()
        delivery, _, body = channel.basic_get(
            queue="device.events",
            auto_ack=False,
        )
        if delivery is None:
            print("No messages available.")
            return

        event = json.loads(body)
        event_id = UUID(event["event_id"])
        occurred_at = datetime.fromisoformat(event["occurred_at"])

        with connect_db() as conn:
            result = process_device_event(
                conn,
                event_id,
                event["device_id"],
                event["event_type"],
                occurred_at,
            )

        channel.basic_ack(delivery_tag=delivery.delivery_tag)
        print(f"{result}: {event_id}")
    finally:
        connection.close()


if __name__ == "__main__":
    consume_one_event()


