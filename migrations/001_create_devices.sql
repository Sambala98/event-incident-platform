CREATE TABLE devices (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    heartbeat_interval_seconds INTEGER NOT NULL DEFAULT 30,
    CONSTRAINT devices_name_not_blank CHECK (btrim(name) <> ''),
    CONSTRAINT devices_heartbeat_range
        CHECK (heartbeat_interval_seconds BETWEEN 5 AND 3600)
);