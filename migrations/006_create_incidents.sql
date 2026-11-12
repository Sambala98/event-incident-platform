CREATE TABLE public.incidents (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    device_id BIGINT NOT NULL REFERENCES public.devices (id),
    opened_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX incidents_one_open_per_device
ON public.incidents (device_id)
WHERE resolved_at IS NULL;