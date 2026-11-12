# Event Incident Platform



A Python backend that tracks device heartbeats and opens an incident when a device misses its configured heartbeat interval.



## How it works



1. FastAPI saves the device event and its outbox row in one PostgreSQL transaction.

2. The publisher sends the pending event to RabbitMQ and records publication after broker confirmation.

3. The consumer uses the event UUID to skip duplicate deliveries. It records the processed event and updates the heartbeat in one PostgreSQL transaction, then acknowledges the message.

4. The incident checker opens an incident for an overdue device and resolves it when a heartbeat arrives after the incident opened and is still fresh.



## Verified scenarios



- **Missed heartbeat.** Router A exceeded its 30-second interval. The checker opened one incident. A second run opened zero additional incidents.

- **Recovery.** A fresh heartbeat went through the API, outbox, RabbitMQ, and consumer. The checker resolved the same incident, and PostgreSQL recorded its `resolved_at` timestamp.



Both scenarios were verified manually. The existing pytest suite passed 12 tests. The publisher, consumer, and incident checker run as separate commands in the local demo.


## Local setup on Windows

Prerequisites: Python, Docker Desktop running Linux containers, and `psql` on PATH.

From the project folder, create the virtual environment and install dependencies:

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```
Create a `.env` file in the project root before starting PostgreSQL. Replace
the placeholder with a local development password. If you are reusing an
existing PostgreSQL database, use the password already set for `incident_app`.

```dotenv
POSTGRES_PASSWORD=replace_with_your_local_password
```

Keep `.env` out of Git.

Start PostgreSQL and check that it is accepting connections:

```cmd
docker compose up -d postgres
docker compose exec postgres pg_isready -U incident_app -d incident_db
```

On an empty database, apply the six migrations in order. Run this as one line
and enter the PostgreSQL password if prompted:

```cmd
psql -h 127.0.0.1 -p 5546 -U incident_app -d incident_db -v ON_ERROR_STOP=1 --single-transaction -f migrations\001_create_devices.sql -f migrations\002_create_device_events.sql -f migrations\003_create_event_outbox.sql -f migrations\004_create_processed_device_events.sql -f migrations\005_add_device_last_heartbeat_at.sql -f migrations\006_create_incidents.sql
```

Verify the application tables:

```cmd
psql -h 127.0.0.1 -p 5546 -U incident_app -d incident_db -c "\dt public.*"
```

The table list should include `devices`, `device_events`, `event_outbox`,
`processed_device_events`, and `incidents`.

## Start RabbitMQ and the API

Create the local RabbitMQ container on the first run:

```cmd
docker run -d --name incident-rabbitmq -p 127.0.0.1:5672:5672 rabbitmq:4
```

If the container already exists and is stopped, start it:

```cmd
docker start incident-rabbitmq
```

Once the broker has started, verify its AMQP listener:

```cmd
docker exec incident-rabbitmq rabbitmq-diagnostics -q check_port_listener 5672
```

In a CMD window with `.venv` active, start FastAPI:

```cmd
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8001 --env-file .env
```

Leave Uvicorn running. In a second CMD window, verify the API:

```cmd
curl.exe -i http://127.0.0.1:8001/health
```

Expect HTTP `200 OK`. This checks the API endpoint. Use the PostgreSQL
and RabbitMQ checks above to verify those services separately.


## Demo: open and resolve a heartbeat incident

Keep the API, PostgreSQL, and RabbitMQ running. Use a second Windows CMD
window in the project folder with `.venv` active. For this demo, use an
empty `device.events` queue and an outbox with no pending events so the
publisher and consumer pick up the heartbeat you just submitted.

### Open one incident

Create a device with a 30-second heartbeat interval:

```cmd
curl.exe -i -X POST "http://127.0.0.1:8001/devices" -H "Content-Type: application/json" -d "{\"name\":\"Demo Router\",\"heartbeat_interval_seconds\":30}"
```

Expect `201 Created`. Set `DEMO_DEVICE_ID` to the returned `id`. For example,
if the API returns `"id": 4`, run:

```cmd
set "DEMO_DEVICE_ID=4"
```

Use a heartbeat from 60 seconds ago to simulate a missed interval:

```cmd
set "DEMO_HEARTBEAT_AGE=60"
```

Run this as one line:

```cmd
python -c "import json, os, uuid; from datetime import datetime, timedelta, timezone; from urllib.request import Request, urlopen; occurred_at = datetime.now(timezone.utc) - timedelta(seconds=int(os.environ['DEMO_HEARTBEAT_AGE'])); event = {'event_id': str(uuid.uuid4()), 'device_id': int(os.environ['DEMO_DEVICE_ID']), 'event_type': 'heartbeat', 'occurred_at': occurred_at.isoformat()}; request = Request('http://127.0.0.1:8001/events', data=json.dumps(event).encode(), headers={'Content-Type': 'application/json'}, method='POST'); response = urlopen(request, timeout=10); print(response.status, response.read().decode())" && python outbox_publisher.py && python event_consumer.py && python incident_checker.py
```

Expect `201`, the same event UUID in the publisher and consumer output,
and an incident opened for your demo device. Run the checker again:

```cmd
python incident_checker.py
```

Expect no additional incident for that device.

### Resolve the incident

Set the heartbeat age to zero:

```cmd
set "DEMO_HEARTBEAT_AGE=0"
```

Rerun the same long command from the previous section. It generates a new
UUID and uses the current UTC time. Expect `Resolved incidents: 1` on an
isolated demo database when the checker runs within 30 seconds.

Verify the incident in PostgreSQL:

```cmd
psql -h 127.0.0.1 -p 5546 -U incident_app -d incident_db -c "SELECT id, device_id, opened_at, resolved_at FROM public.incidents WHERE device_id = %DEMO_DEVICE_ID% ORDER BY id;"
```

Expect one incident row for the demo device with a timestamp in `resolved_at`.