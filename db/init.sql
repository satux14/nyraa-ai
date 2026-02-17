CREATE TABLE IF NOT EXISTS analysis_logs (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_type TEXT NOT NULL DEFAULT 'guest',
    customer_name TEXT,
    skin_type TEXT,
    acne_level TEXT,
    face_shape TEXT,
    dark_circle_score TEXT,
    recommended_services JSONB,
    recommended_products JSONB
);

ALTER TABLE analysis_logs ADD COLUMN IF NOT EXISTS dark_circle_score TEXT;
ALTER TABLE analysis_logs ADD COLUMN IF NOT EXISTS user_type TEXT;
ALTER TABLE analysis_logs ADD COLUMN IF NOT EXISTS customer_name TEXT;
UPDATE analysis_logs SET user_type = 'guest' WHERE user_type IS NULL;

