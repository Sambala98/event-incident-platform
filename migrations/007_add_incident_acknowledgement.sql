ALTER TABLE public.incidents
    ADD COLUMN acknowledged_by TEXT,
    ADD COLUMN acknowledged_at TIMESTAMPTZ,
    ADD CONSTRAINT incidents_acknowledgement_pair CHECK (
        (acknowledged_by IS NULL AND acknowledged_at IS NULL)
        OR
        (
            acknowledged_by IS NOT NULL
            AND btrim(acknowledged_by) <> ''
            AND acknowledged_at IS NOT NULL
        )
    );