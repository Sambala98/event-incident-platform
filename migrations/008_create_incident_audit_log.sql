CREATE TABLE public.incident_audit_log (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    incident_id BIGINT NOT NULL REFERENCES public.incidents (id),
    action TEXT NOT NULL CHECK (action IN ('acknowledged', 'resolved')),
    actor TEXT NOT NULL CHECK (btrim(actor) <> ''),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);