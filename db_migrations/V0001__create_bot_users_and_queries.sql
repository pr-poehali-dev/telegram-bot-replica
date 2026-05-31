
CREATE TABLE IF NOT EXISTS t_p73400739_telegram_bot_replica.bot_users (
    id BIGINT PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    language_code TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS t_p73400739_telegram_bot_replica.bot_queries (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    query_type TEXT NOT NULL,
    query_value TEXT,
    result JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bot_queries_user_id ON t_p73400739_telegram_bot_replica.bot_queries(user_id);
CREATE INDEX IF NOT EXISTS idx_bot_queries_created_at ON t_p73400739_telegram_bot_replica.bot_queries(created_at);
