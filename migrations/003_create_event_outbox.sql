CREATE TABLE public.event_outbox (
    event_id UUID PRIMARY KEY REFERENCES public.device_events (event_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMPTZ
);