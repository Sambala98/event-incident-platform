CREATE TABLE public.processed_device_events (
    event_id UUID PRIMARY KEY REFERENCES public.device_events (event_id),
    processed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);