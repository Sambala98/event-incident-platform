import json
import pika
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv(".env")

from main import connect_db


def read_pending_events():
    with connect_db() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    o.event_id,
                    e.device_id,
                    e.event_type,
                    e.occurred_at
                FROM public.event_outbox AS o
                JOIN public.device_events AS e
                    ON e.event_id = o.event_id
                WHERE o.published_at IS NULL
                ORDER BY o.created_at, o.event_id
                LIMIT 10
                """
            )
            return cursor.fetchall()

def build_event_message(event):
    payload = {
        "event_id": str(event["event_id"]),
        "device_id": event["device_id"],
        "event_type": event["event_type"],
        "occurred_at": event["occurred_at"].isoformat(),
    }
    return json.dumps(payload)
def publish_one_pending_event():
    events = read_pending_events()
    if not events:
        print("No pending events.")
        return

    event = events[0]
    queue_name = "device.events"
    params = pika.ConnectionParameters(host="127.0.0.1", port=5672)
    connection = pika.BlockingConnection(params)

    try:
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        channel.confirm_delivery()
        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=build_event_message(event).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
                message_id=str(event["event_id"]),
            ),
            mandatory=True,
        )

        with connect_db() as conn:
            conn.execute(
                """
                UPDATE public.event_outbox
                SET published_at = CURRENT_TIMESTAMP
                WHERE event_id = %s AND published_at IS NULL
                """,
                (event["event_id"],),
            )

        print(f"Published and recorded {event['event_id']}")
    finally:
        connection.close()


if __name__ == "__main__":
    publish_one_pending_event()