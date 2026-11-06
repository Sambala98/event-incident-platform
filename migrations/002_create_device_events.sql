CREATE TABLE public.device_events (
    event_id UUID PRIMARY KEY,
    device_id BIGINT NOT NULL REFERENCES public.devices (id),
    event_type TEXT NOT NULL CHECK (event_type IN ('heartbeat', 'fault')),
    occurred_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);