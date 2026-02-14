CREATE TABLE IF NOT EXISTS analysis_logs (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    skin_type TEXT,
    acne_level TEXT,
    face_shape TEXT,
    recommended_services JSONB,
    recommended_products JSONB
);

