from outbox_publisher import connect_db


def read_heartbeat_statuses():
    with connect_db() as conn:
        return conn.execute(
            """
            SELECT
                id,
                name,
                last_heartbeat_at AT TIME ZONE 'America/Los_Angeles'
                    AS last_heartbeat_pacific,
                heartbeat_interval_seconds,
                CASE
                    WHEN last_heartbeat_at IS NULL THEN 'unknown'
                    WHEN CURRENT_TIMESTAMP >
                         last_heartbeat_at
                         + heartbeat_interval_seconds * INTERVAL '1 second'
                        THEN 'overdue'
                    ELSE 'within_interval'
                END AS heartbeat_status
            FROM public.devices
            ORDER BY id
            """
        ).fetchall()


if __name__ == "__main__":
    for device in read_heartbeat_statuses():
        print(
            f"{device['name']}: {device['heartbeat_status']} "
            f"(last heartbeat in Pacific time: {device['last_heartbeat_pacific']})"
        )