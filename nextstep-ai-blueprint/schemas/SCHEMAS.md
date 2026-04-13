# SCHEMAS.md — Data Structures

## SQLite Schema

```sql
-- database/schema.sql

-- Enable WAL mode for better concurrent read performance
PRAGMA journal_mode=WAL;

-- ============================================
-- Layer 1: Raw Memory
-- Everything that happened, unfiltered
-- ============================================
CREATE TABLE IF NOT EXISTS raw_memory (
    id              TEXT PRIMARY KEY,
    timestamp       TEXT NOT NULL,           -- ISO 8601 UTC
    type            TEXT NOT NULL            -- 'user_query' | 'model_response' | 'insight_generated' | 'user_feedback' | 'report_generated'
        CHECK(type IN ('user_query', 'model_response', 'insight_generated', 'user_feedback', 'report_generated')),
    content         TEXT NOT NULL,
    session_id      TEXT NOT NULL,
    model_used      TEXT,                    -- 'claude' | 'gpt' | null
    metadata        TEXT                     -- JSON string
);

CREATE INDEX IF NOT EXISTS idx_raw_session ON raw_memory(session_id);
CREATE INDEX IF NOT EXISTS idx_raw_timestamp ON raw_memory(timestamp);
CREATE INDEX IF NOT EXISTS idx_raw_type ON raw_memory(type);

-- ============================================
-- Layer 2: Canonical Memory
-- Structured units extracted from raw interactions
-- ============================================
CREATE TABLE IF NOT EXISTS canonical_units (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    timestamp       TEXT NOT NULL,
    unit_type       TEXT NOT NULL            -- 'question' | 'decision' | 'claim' | 'task' | 'open_question' | 'correction' | 'topic'
        CHECK(unit_type IN ('question', 'decision', 'claim', 'task', 'open_question', 'correction', 'topic')),
    summary         TEXT NOT NULL,           -- One-line summary
    content         TEXT NOT NULL,           -- Full content
    topic_tags      TEXT,                    -- JSON array: ["coaching", "architecture"]
    status          TEXT DEFAULT 'active'    -- 'active' | 'superseded' | 'corrected'
        CHECK(status IN ('active', 'superseded', 'corrected'))
);

CREATE INDEX IF NOT EXISTS idx_canonical_session ON canonical_units(session_id);
CREATE INDEX IF NOT EXISTS idx_canonical_type ON canonical_units(unit_type);
CREATE INDEX IF NOT EXISTS idx_canonical_status ON canonical_units(status);

-- ============================================
-- Insights: Observer findings
-- ============================================
CREATE TABLE IF NOT EXISTS insights (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    timestamp       TEXT NOT NULL,
    insight_type    TEXT NOT NULL            -- 'informational' | 'inferential' | 'complementary'
        CHECK(insight_type IN ('informational', 'inferential', 'complementary')),
    routing_class   TEXT NOT NULL            -- 'A' | 'B' | 'C' | 'D'
        CHECK(routing_class IN ('A', 'B', 'C', 'D')),
    content         TEXT NOT NULL,           -- The missing angle text
    evidence        TEXT,                    -- JSON: why this was generated
    routing_reason  TEXT,                    -- Why this routing class
    surfaced        INTEGER DEFAULT 0,       -- 0=queued, 1=shown immediately
    user_reaction   TEXT                     -- 'engaged' | 'ignored' | 'dismissed' | 'asked_more' | null
        CHECK(user_reaction IN ('engaged', 'ignored', 'dismissed', 'asked_more', NULL)),
    quality_score   INTEGER                  -- 1-5, self-rated by user (nullable)
        CHECK(quality_score BETWEEN 1 AND 5),
    report_id       TEXT                     -- FK to daily_reports.id (nullable)
);

CREATE INDEX IF NOT EXISTS idx_insights_session ON insights(session_id);
CREATE INDEX IF NOT EXISTS idx_insights_routing ON insights(routing_class);
CREATE INDEX IF NOT EXISTS idx_insights_surfaced ON insights(surfaced);

-- ============================================
-- Sessions
-- ============================================
CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    started_at      TEXT NOT NULL,
    ended_at        TEXT,
    queries_count   INTEGER DEFAULT 0,
    insights_count  INTEGER DEFAULT 0,
    alerts_count    INTEGER DEFAULT 0,
    model_default   TEXT                     -- 'claude' | 'gpt'
);

-- ============================================
-- Daily Reports
-- ============================================
CREATE TABLE IF NOT EXISTS daily_reports (
    id              TEXT PRIMARY KEY,
    date            TEXT NOT NULL UNIQUE,     -- YYYY-MM-DD
    generated_at    TEXT NOT NULL,
    content         TEXT NOT NULL,            -- Full report markdown
    insights_count  INTEGER,
    sessions_count  INTEGER,
    engagement_rate REAL                      -- 0.0-1.0
);

CREATE INDEX IF NOT EXISTS idx_reports_date ON daily_reports(date);
```

## Data Contracts Between Agents

### Collector Output → Orchestrator
```json
{
    "type": "analytical",
    "language": "mixed",
    "word_count": 45,
    "estimated_complexity": "moderate"
}
```

### Memory Store Input
```json
{
    "query": "أريد بناء أداة كوتشينج",
    "response": "Here's how to build a coaching tool...",
    "session_id": "sess_abc123",
    "model_used": "claude",
    "classification": {
        "type": "creative",
        "language": "ar",
        "word_count": 5,
        "estimated_complexity": "complex"
    }
}
```

### Memory Retrieval Output → Context Agent
```json
[
    {
        "id": "cu_xyz789",
        "unit_type": "decision",
        "summary": "Decided to use ICF standards for coaching tool",
        "content": "...",
        "topic_tags": ["coaching", "standards"],
        "timestamp": "2026-04-10T14:30:00Z"
    },
    {
        "id": "cu_abc456",
        "unit_type": "claim",
        "summary": "CBT is sufficient foundation for assessment",
        "content": "...",
        "topic_tags": ["coaching", "CBT"],
        "timestamp": "2026-04-09T10:15:00Z"
    }
]
```

### Insight Agent Output
```json
{
    "has_insight": true,
    "angles": [
        {
            "type": "informational",
            "content": "هناك معايير ICF محددة للكفاءات لم تُذكر — الأداة تحتاج الالتزام بها",
            "evidence": "User asked about coaching tool without mentioning ICF competency standards which are required for professional coaching tools",
            "routing_class": "C",
            "routing_reason": "Useful knowledge gap but not time-sensitive — belongs in daily report"
        }
    ],
    "skip_reason": null
}
```

### Insight Agent Output — No Finding
```json
{
    "has_insight": false,
    "angles": [],
    "skip_reason": "The model's answer covered the topic comprehensively and the user's question showed familiarity with the domain"
}
```

### Observer Router Output
```
"alert_now" | "queue_report" | "suppress"
```

### Synthesis Composer Output (Daily Report)
```markdown
# تقرير يومي — 12 أبريل 2026

## النتائج الرئيسية
- **معايير ICF للكوتشينج**: أداة الكوتشينج تحتاج الالتزام بمعايير الكفاءات...
- **تعارض مع قرار سابق**: الميزانية المحددة اليوم تتعارض مع...

## أنماط ملاحظة
- موضوع الكوتشينج ظهر 3 مرات هذا الأسبوع بدون تقدم تنفيذي

## أسئلة جاهزة
1. ما الفرق بين ICF-ACC و ICF-PCC ومتى أحتاج كل منهما؟
2. هل الميزانية الجديدة تغيير مدروس أم قرار لحظي؟

## إحصائيات
- التفاعلات: 8
- الملاحظات المولّدة: 5
- التفاعل مع الملاحظات: 60%
- المواضيع: كوتشينج، ميزانية، معمارية
```

## Canonical Unit Extraction Rules (Phase 1 — Simple)

Since there's no LLM for extraction in Phase 1, use these simple rules:

```python
def extract_canonical_units(query: str, response: str, classification: dict) -> list:
    """
    Phase 1: Simple rule-based extraction.
    Always creates at least a 'question' unit from the query.
    """
    units = []
    
    # Every query becomes a 'question' unit
    units.append({
        "unit_type": "question",
        "summary": query[:100],  # First 100 chars as summary
        "content": query,
        "topic_tags": extract_topic_tags(query)  # keyword-based
    })
    
    # If classification is 'decision' → also create a 'decision' unit
    if classification["type"] == "decision":
        units.append({
            "unit_type": "decision",
            "summary": f"Decision context: {query[:80]}",
            "content": f"Q: {query}\nA: {response[:500]}",
            "topic_tags": extract_topic_tags(query)
        })
    
    return units


def extract_topic_tags(text: str) -> list:
    """
    Phase 1: Simple keyword extraction.
    Look for domain-specific terms in the text.
    """
    # Predefined topic keywords (expand as needed)
    topic_keywords = {
        "coaching": ["coaching", "كوتشينج", "ICF", "competency"],
        "architecture": ["architecture", "معمارية", "system design", "agent"],
        "business": ["budget", "ميزانية", "pricing", "revenue", "cost"],
        "ai": ["model", "LLM", "prompt", "RAG", "fine-tuning"],
        "product": ["MVP", "feature", "user", "UX", "onboarding"],
        # Add more as domains emerge
    }
    
    text_lower = text.lower()
    tags = []
    for tag, keywords in topic_keywords.items():
        if any(kw.lower() in text_lower for kw in keywords):
            tags.append(tag)
    
    return tags if tags else ["general"]
```

## Context Assembly (max 800 tokens)

```python
def build_context_block(relevant_units: list, max_chars: int = 3200) -> str:
    """
    Build context string from relevant canonical units.
    800 tokens ≈ 3200 characters (rough estimate).
    Most recent first, truncate when limit reached.
    """
    block = ""
    for unit in relevant_units:
        entry = f"[{unit['timestamp'][:10]}] ({unit['unit_type']}) {unit['summary']}\n"
        if len(block) + len(entry) > max_chars:
            break
        block += entry
    return block if block else "No prior context available."
```
