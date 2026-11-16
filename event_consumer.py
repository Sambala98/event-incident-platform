import json
from datetime import datetime
from uuid import UUID
from psycopg.errors import ConnectionTimeout

import pika
from pydantic import ValidationError

from outbox_publisher import connect_db
from schemas import EventCreate


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
def publish_to_dlq(channel, body):
    channel.queue_declare(queue="device.events.dlq", durable=True)
    channel.confirm_delivery()
    channel.basic_publish(
        exchange="",
        routing_key="device.events.dlq",
        body=body,
        properties=pika.BasicProperties(delivery_mode=2),
        mandatory=True,
    )
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

        try:
            event = EventCreate.model_validate_json(body)
        except ValidationError:
            channel.queue_declare(queue="device.events.dlq", durable=True)
            channel.confirm_delivery()
            channel.basic_publish(
                exchange="",
                routing_key="device.events.dlq",
                body=body,
                properties=pika.BasicProperties(delivery_mode=2),
                mandatory=True,
            )
            channel.basic_ack(delivery_tag=delivery.delivery_tag)
            print("Invalid event moved to device.events.dlq")
            return

        max_attempts = 3

        for attempt in range(1, max_attempts + 1):
            try:
                with connect_db() as conn:
                    result = process_device_event(
                        conn,
                        event.event_id,
                        event.device_id,
                        event.event_type,
                        event.occurred_at,
                    )
            except ConnectionTimeout:
                print(
                    f"Database connection timed out for {event.event_id} "
                    f"(attempt {attempt}/{max_attempts})",
                    flush=True,
                )
                if attempt == max_attempts:
                     publish_to_dlq(channel, body)
                     channel.basic_ack(delivery_tag=delivery.delivery_tag)
                     print(f"Retry limit reached for {event.event_id}. Moved to device.events.dlq.")
                     return

    finally:
        connection.close()


if __name__ == "__main__":
    consume_one_event()
