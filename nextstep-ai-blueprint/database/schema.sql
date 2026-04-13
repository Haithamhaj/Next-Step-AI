PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS conversations (
    id                    TEXT PRIMARY KEY,
    label                 TEXT NOT NULL,
    source                TEXT NOT NULL,
    content               TEXT NOT NULL,
    compressed_content    TEXT,
    added_at              TEXT NOT NULL,
    word_count            INTEGER,
    compressed_word_count INTEGER,
    status                TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'analyzed')),
    analyzed_at           TEXT
);

CREATE TABLE IF NOT EXISTS canonical_units (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    timestamp       TEXT NOT NULL,
    unit_type       TEXT NOT NULL CHECK(unit_type IN ('question', 'decision', 'claim', 'task', 'open_question', 'correction', 'topic')),
    summary         TEXT NOT NULL,
    content         TEXT NOT NULL,
    topic_tags      TEXT,
    status          TEXT DEFAULT 'active' CHECK(status IN ('active', 'superseded', 'corrected'))
);

CREATE TABLE IF NOT EXISTS insights (
    id              TEXT PRIMARY KEY,
    report_id       TEXT,
    conversation_id TEXT,
    timestamp       TEXT NOT NULL,
    insight_type    TEXT NOT NULL CHECK(insight_type IN ('informational', 'inferential', 'complementary', 'pattern')),
    content         TEXT NOT NULL,
    evidence        TEXT,
    impact          TEXT DEFAULT 'medium' CHECK(impact IN ('high', 'medium', 'low')),
    quality_score   INTEGER CHECK(quality_score BETWEEN 1 AND 5),
    conversations_referenced TEXT,
    missing_angle   TEXT,
    why_it_matters  TEXT,
    ready_prompt    TEXT,
    confidence      TEXT,
    confidence_reason TEXT,
    profile_connection TEXT
);

CREATE TABLE IF NOT EXISTS daily_reports (
    id              TEXT PRIMARY KEY,
    date            TEXT NOT NULL,
    timestamp       TEXT NOT NULL,
    report_content  TEXT NOT NULL,
    insights_count  INTEGER,
    sessions_count  INTEGER
    -- engagement_rate column intentionally omitted (dead data — no longer written)
);

CREATE TABLE IF NOT EXISTS contextual_instructions (
    id              TEXT PRIMARY KEY,
    report_id       TEXT,
    timestamp       TEXT NOT NULL,
    content         TEXT NOT NULL,
    topic_summary   TEXT,
    lang            TEXT
);

CREATE TABLE IF NOT EXISTS research_results (
    id              TEXT PRIMARY KEY,
    report_id       TEXT,
    timestamp       TEXT NOT NULL,
    topic_summary   TEXT,
    discoveries     TEXT,
    search_queries  TEXT,
    research_summary TEXT
);
