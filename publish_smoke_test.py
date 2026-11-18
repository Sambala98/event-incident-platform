import pika

from outbox_publisher import build_event_message, read_pending_events


def main():
    events = read_pending_events()
    if not events:
        print("No pending events to test.")
        return

    event = events[0]
    queue_name = "device.events.smoke"
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
        print(f"RabbitMQ confirmed {event['event_id']} on {queue_name}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()