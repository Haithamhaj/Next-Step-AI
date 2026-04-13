# ARCHITECTURE.md — System Design

## Data Flow

```
User types query
       │
       ▼
┌──────────────┐
│  Collector    │ ← Rules only: classify type + language + complexity
│  (no LLM)    │
└──────┬───────┘
       │ classification dict
       ▼
┌──────────────┐
│  Base Model   │ ← Claude API or GPT API (user's choice)
│  (API call)   │
└──────┬───────┘
       │ answer text
       ▼
┌──────────────┐
│  UI Display   │ ← Answer shown IMMEDIATELY to user (streaming)
└──────┬───────┘
       │
       ▼ ── (everything below happens in background) ──
       │
┌──────────────┐
│Memory Agent   │ ← Store raw + extract canonical units
│  (SQLite)     │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Should we    │ ← Collector said "executive + simple"? → STOP here
│  analyze?     │
└──────┬───────┘
       │ yes
       ▼
┌──────────────┐
│Context Agent  │ ← Pull last N relevant interactions from memory
│  (Python)     │    Build context block (max 800 tokens)
└──────┬───────┘
       │ context block
       ▼
┌──────────────┐
│Insight Agent  │ ← Claude API call with: query + answer + context + profile
│ (Claude API)  │    Returns: missing angles (or "none")
└──────┬───────┘
       │ insight JSON
       ▼
┌──────────────┐
│  Observer     │ ← Rules: classify A/B/C/D → route to alert or queue
│  Router       │
│  (no LLM)     │
└──────┬───────┘
       │
  ┌────┴────┐
  ▼         ▼
Alert    Queue for
(UI)     daily report
```

## Daily Report Flow (Separate from per-interaction)

```
User clicks "Generate Report" (or auto-trigger at end of day)
       │
       ▼
┌──────────────┐
│ Memory Agent  │ ← Fetch all queued insights for today
└──────┬───────┘
       │ list of insights + their sessions
       ▼
┌──────────────┐
│  Synthesis    │ ← GPT API: produce structured daily report
│  Composer     │
│  (GPT API)    │
└──────┬───────┘
       │ markdown report
       ▼
┌──────────────┐
│ Store report  │ ← Save to daily_reports table + reports/ folder
│ Display in UI │
└──────────────┘
```

## Agent Contracts

### Collector Agent
```
Input:  raw query string
Output: {
    "type": "executive|analytical|creative|decision|exploration",
    "language": "ar|en|mixed",
    "word_count": int,
    "estimated_complexity": "simple|moderate|complex"
}
Side effects: NONE
LLM: NO
```

### Memory Agent
```
Input (store):  query, response, session_id, model_used, classification
Output: raw_memory_id, canonical_unit_ids

Input (retrieve): query text, limit
Output: list of relevant canonical units (max 800 tokens total)

Side effects: writes to SQLite
LLM: NO
```

### Context Agent (embedded in orchestrator for Phase 1)
```
Input:  current query, relevant canonical units, user profile
Output: formatted context string for Insight Agent prompt (≤800 tokens)
Side effects: NONE
LLM: NO
```

### Insight Agent
```
Input:  system prompt + user prompt (query, answer, context, profile)
Output: {
    "has_insight": bool,
    "angles": [
        {
            "type": "informational|inferential|complementary",
            "content": "...",
            "evidence": "...",
            "routing_class": "A|B|C|D",
            "routing_reason": "..."
        }
    ],
    "skip_reason": "..." (only if has_insight is false)
}
Side effects: NONE (does not store — orchestrator handles that)
LLM: YES — Claude Sonnet
```

### Observer Router
```
Input:  insight dict, classification dict, session silence state
Output: "alert_now" | "queue_report" | "suppress"
Side effects: NONE
LLM: NO

Decision Tree:
1. silence_policy active? → suppress
2. classification.type == "executive"?
   - routing_class == "A" → alert_now
   - else → suppress
3. routing_class == "A" → alert_now
4. routing_class == "B" → queue_report (priority: high)
5. routing_class == "C" or "D" → queue_report (priority: normal)
```

### Synthesis Composer
```
Input:  list of today's queued insights with their sessions
Output: markdown report string
Side effects: NONE (orchestrator stores the report)
LLM: YES — GPT-4o
```

## Orchestrator — The Central Coordinator

The orchestrator is the ONLY file that calls agents. Agents never call each other.

```python
# Pseudocode for orchestrator.py

async def handle_interaction(query: str, model_choice: str) -> dict:
    # 1. Classify
    classification = collector.classify(query)
    
    # 2. Get base answer (STREAM to user)
    answer = await base_model.call(query, model_choice)
    
    # 3. Store in memory
    session_id = get_session()
    memory.store(query, answer, session_id, model_choice, classification)
    
    # 4. Skip insight for simple executive queries
    if should_skip(classification):
        return {"answer": answer, "alert": None}
    
    # 5. Get context
    context = memory.get_relevant(query, limit=5)
    profile = load_profile()
    
    # 6. Generate insight
    insight = await insight_agent.analyze(query, answer, context, profile)
    
    # 7. Route
    if insight["has_insight"]:
        for angle in insight["angles"]:
            action = observer.route(angle, classification, session_id)
            memory.store_insight(angle, session_id, surfaced=(action == "alert_now"))
            if action == "alert_now":
                return {"answer": answer, "alert": angle}
    
    return {"answer": answer, "alert": None}


def generate_daily_report(date: str) -> str:
    insights = memory.get_queued_insights(date)
    if not insights:
        return "لا توجد نتائج مهمة اليوم"
    
    report = synthesis.compose(insights)
    memory.store_report(date, report)
    save_report_file(date, report)
    return report
```

## Silence Policy State Machine

```
Session starts → Observer ACTIVE
       │
       ▼
  Insight generated → shown to user
       │
       ├── User engaged → reset ignore counter
       │
       └── User ignored → increment ignore counter
                │
                ├── counter < 3 → Observer ACTIVE
                │
                └── counter >= 3 → Observer SILENT for rest of session
                         │
                         └── New session → Observer ACTIVE (reset)
```

## Error Recovery

| Failure | Impact | Recovery |
|---------|--------|----------|
| Insight API fails | No insight this interaction | Log error, continue — user sees answer normally |
| Base model API fails | No answer | Show error to user, suggest switching model |
| SQLite write fails | Data loss risk | Retry once, if fails → log to fallback text file |
| Synthesis API fails | No daily report | Show error, offer to retry, show raw insights list instead |
| Streamlit crashes | Full UI down | Standard Streamlit error page, session state preserved |
