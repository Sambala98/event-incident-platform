from outbox_publisher import connect_db


def open_overdue_incidents():
    with connect_db() as conn:
        opened = conn.execute(
            """
            INSERT INTO public.incidents (device_id)
            SELECT d.id
            FROM public.devices AS d
            WHERE d.last_heartbeat_at IS NOT NULL
              AND CURRENT_TIMESTAMP >
                  d.last_heartbeat_at
                  + d.heartbeat_interval_seconds * INTERVAL '1 second'
            ON CONFLICT (device_id) WHERE resolved_at IS NULL DO NOTHING
            RETURNING id, device_id
            """
        ).fetchall()

    return opened


def resolve_recovered_incidents():
    with connect_db() as conn:
        resolved = conn.execute(
            """
            WITH resolved AS (
                UPDATE public.incidents AS i
                SET resolved_at = CURRENT_TIMESTAMP
                FROM public.devices AS d
                WHERE i.device_id = d.id
                  AND i.resolved_at IS NULL
                  AND d.last_heartbeat_at > i.opened_at
                  AND CURRENT_TIMESTAMP <=
                      d.last_heartbeat_at
                      + d.heartbeat_interval_seconds * INTERVAL '1 second'
                RETURNING i.id, i.device_id, i.resolved_at
            ),
            logged AS (
                INSERT INTO public.incident_audit_log
                    (incident_id, action, actor, created_at)
                SELECT id, 'resolved', 'system', resolved_at
                FROM resolved
                RETURNING incident_id
            )
            SELECT r.id, r.device_id
            FROM resolved AS r
            JOIN logged AS l ON l.incident_id = r.id
            """
        ).fetchall()

    return resolved
if __name__ == "__main__":
    incidents = open_overdue_incidents()
    print(f"Opened incidents: {len(incidents)}")
    for incident in incidents:
        print(f"Incident {incident['id']} opened for device {incident['device_id']}")
    resolved = resolve_recovered_incidents()
    print(f"Resolved incidents: {len(resolved)}")