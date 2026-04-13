# Next-Step AI — Phase 1 Technical Specification

**Version: 1.0 | April 2026**
**Reference: Vision Document v3.2**

---

## 1. Scope — What Phase 1 Builds

Phase 1 proves one hypothesis: **Observer can generate genuinely useful missing angles — measurably.**

What is IN scope:
- Simple web UI (Streamlit)
- Base model interaction (Claude API + GPT API)
- Insight Agent (missing angle generation via API)
- Observer routing (Class A/B/C/D via rules)
- Memory (SQLite — Raw + Canonical layers only)
- Daily Report (accumulated findings as structured page)
- Immediate Alert (Class A findings shown inline)
- 30 real interactions as the test dataset

What is NOT in scope:
- Graph Memory / Graphiti / Zep
- Derived Maps (Cognitive, Behavioral, Personal)
- Delta Layer
- Calibration Agent
- Fine-tuning / GEPA+DSPy
- Local models
- External sources (LinkedIn/CV/GitHub)
- Psychological layer

---

## 2. Architecture — Phase 1

```
User (Browser) → Streamlit UI → Orchestrator
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
              Collector       Base Model        Memory Agent
              (rules)        (Claude/GPT)       (SQLite)
                    │               │               │
                    └───────┬───────┘               │
                            │                       │
                      Insight Agent ◄───────────────┘
                      (Claude API)        (retrieves context)
                            │
                      Observer Router
                      (rules-based)
                            │
                    ┌───────┴───────┐
                    │               │
              Class A Alert    Class B/C/D
              (immediate)      (daily report)
                    │               │
                    └───────┬───────┘
                            │
                    Synthesis Composer
                      (GPT API)
                            │
                      Report / Alert
```

### Agent Implementation Map

| Agent | Implementation | Model | Cost per interaction |
|-------|---------------|-------|---------------------|
| Collector | Python rules | None | Free |
| Base Model | API call | Claude or GPT (user choice per query) | ~$0.01-0.05 |
| Memory Agent | Python + SQLite | None | Free |
| Context Agent | Python (query builder) | None | Free |
| Insight Agent | API call | Claude Sonnet | ~$0.01-0.03 |
| Observer Router | Python rules (decision tree) | None | Free |
| Synthesis Composer | API call (daily only) | GPT-4o | ~$0.02-0.05 |
| **Total per interaction** | | | **~$0.03-0.10** |

---

## 3. Data Schemas

### 3.1 Raw Memory (Layer 1)

```sql
CREATE TABLE raw_memory (
    id              TEXT PRIMARY KEY,    -- UUID
    timestamp       TEXT NOT NULL,       -- ISO 8601
    type            TEXT NOT NULL,       -- 'user_query' | 'model_response' | 'insight' | 'user_feedback'
    content         TEXT NOT NULL,       -- The actual text
    session_id      TEXT NOT NULL,       -- Groups a Q&A pair
    model_used      TEXT,                -- 'claude' | 'gpt' | null
    metadata        TEXT                 -- JSON: {topic_tags, word_count, language}
);
```

### 3.2 Canonical Memory (Layer 2)

```sql
CREATE TABLE canonical_units (
    id              TEXT PRIMARY KEY,    -- UUID
    session_id      TEXT NOT NULL,       -- Links to raw_memory
    timestamp       TEXT NOT NULL,
    unit_type       TEXT NOT NULL,       -- 'question' | 'decision' | 'claim' | 'task' | 'open_question' | 'correction'
    summary         TEXT NOT NULL,       -- One-line summary of the unit
    content         TEXT NOT NULL,       -- Full content
    topic_tags      TEXT,                -- JSON array: ["coaching", "architecture"]
    confidence      REAL DEFAULT 0.5,   -- 0.0-1.0
    status          TEXT DEFAULT 'active' -- 'active' | 'superseded' | 'corrected'
);
```

### 3.3 Insights (Observer findings)

```sql
CREATE TABLE insights (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    timestamp       TEXT NOT NULL,
    insight_type    TEXT NOT NULL,       -- 'informational' | 'inferential' | 'complementary'
    routing_class   TEXT NOT NULL,       -- 'A' | 'B' | 'C' | 'D'
    content         TEXT NOT NULL,       -- The missing angle text
    evidence        TEXT,                -- JSON: what triggered this insight
    surfaced        INTEGER DEFAULT 0,  -- 0=queued, 1=shown to user
    user_reaction   TEXT,                -- 'engaged' | 'ignored' | 'dismissed' | 'asked_more' | null
    report_id       TEXT                 -- Which daily report included this
);
```

### 3.4 Daily Reports

```sql
CREATE TABLE daily_reports (
    id              TEXT PRIMARY KEY,
    date            TEXT NOT NULL,       -- YYYY-MM-DD
    generated_at    TEXT NOT NULL,
    content         TEXT NOT NULL,       -- Full report markdown
    insights_count  INTEGER,
    sessions_count  INTEGER
);
```

### 3.5 Sessions

```sql
CREATE TABLE sessions (
    id              TEXT PRIMARY KEY,
    started_at      TEXT NOT NULL,
    ended_at        TEXT,
    queries_count   INTEGER DEFAULT 0,
    model_default   TEXT                 -- 'claude' | 'gpt'
);
```

---

## 4. Agent Specifications

### 4.1 Collector Agent (Rules-Based)

No LLM. Pure Python.

**Input:** User's raw query text
**Output:** Classified event

```python
def classify_query(query: str) -> dict:
    """
    Returns:
    {
        "type": "executive" | "analytical" | "creative" | "decision" | "exploration",
        "language": "ar" | "en" | "mixed",
        "word_count": int,
        "estimated_complexity": "simple" | "moderate" | "complex"
    }
    """
```

Classification rules:
- **Executive**: contains action keywords (translate, format, fix, send, write email, draft)
- **Decision**: contains decision keywords (should I, which is better, compare, choose, decide)
- **Analytical**: contains analysis keywords (why, how does, explain, analyze, what causes)
- **Exploration**: contains exploration keywords (what if, imagine, explore, brainstorm)
- **Creative**: contains creative keywords (design, create, build, make)
- Language detection: Arabic chars > 50% → "ar", < 20% → "en", else → "mixed"

**Observer skip rule:** If type == "executive" AND complexity == "simple" → skip Insight Agent entirely.

### 4.2 Memory Agent (Python + SQLite)

No LLM. Pure Python.

**Responsibilities:**
1. Store every interaction in raw_memory
2. Extract canonical units from Q&A pairs (simple rule-based for Phase 1)
3. Retrieve relevant past context for Insight Agent

**Context retrieval logic (Phase 1 — simple):**
```python
def get_relevant_context(query: str, limit: int = 5) -> list:
    """
    Phase 1: keyword matching against canonical_units.
    - Extract topic tags from current query
    - Match against stored canonical_units with same tags
    - Return last N matches ordered by recency
    - Maximum context: 500-800 tokens
    """
```

### 4.3 Insight Agent (Claude API)

The core of Phase 1. Single API call per interaction.

**System Prompt:**

```
You are the Insight Agent for Next-Step AI. Your role is to analyze a user's question and the model's answer, then identify genuinely missing angles.

## Your Task
Given:
- The user's question
- The model's answer
- Past context from previous interactions (if available)
- The user's cognitive profile (if available)

Identify missing angles that fall into one of three types:
1. INFORMATIONAL — a missing concept, standard, framework, or domain fact that the user clearly doesn't know
2. INFERENTIAL — a hidden assumption, contradiction, or conflict with prior context
3. COMPLEMENTARY — an adjacent dimension required for better execution or decision quality

## Rules
- Only surface angles that MATERIALLY improve the user's next step
- Never repeat what the answer already covered
- Never surface obvious information the user likely already knows
- If nothing genuinely useful is missing → return "none"
- Maximum 2 angles per interaction
- Each angle must be specific and actionable — not vague advice
- Prefer: "There is an ICF standard for coaching certification you should consider"
  Over: "You might want to look into industry standards"

## Anti-Filler Check
Before outputting, verify each angle passes ALL of these:
- Would an expert in this domain consider this non-obvious?
- Does this change what the user would do next?
- Is this specific enough to act on?
- If the user said "I already know this" — would that be surprising?

If any check fails → drop the angle.

## Output Format (JSON)
{
    "has_insight": true/false,
    "angles": [
        {
            "type": "informational|inferential|complementary",
            "content": "The specific missing angle in the user's language",
            "evidence": "Why this is genuinely missing based on the question/context",
            "routing_class": "A|B|C|D",
            "routing_reason": "Why this class"
        }
    ],
    "skip_reason": "Only if has_insight is false — why nothing was worth surfacing"
}

## Routing Classes
- A (Immediate Alert): Value materially drops if delayed. Live contradiction with a recent decision.
- B (Near-term): Useful soon but not interruptive. Relevant to current work session.
- C (Daily Report): Emerges across time, gains value through accumulation.
- D (Evergreen): Persistent gap — useful but not urgent.

## Language
Respond in the same language the user used. If mixed Arabic/English, use mixed.
```

**User Prompt Template:**

```
## User's Question
{user_query}

## Model's Answer
{model_response}

## Past Context (last {n} relevant interactions)
{context_block}

## User's Known Profile
{cognitive_profile}

Analyze for missing angles.
```

### 4.4 Observer Router (Rules-Based)

No LLM. Decision tree.

```python
def route_insight(insight: dict, query_classification: dict) -> str:
    """
    Input: insight from Insight Agent + query classification from Collector
    Output: action — 'alert_now' | 'queue_report' | 'suppress'
    """
    
    # Rule 1: Executive queries → suppress unless Class A
    if query_classification["type"] == "executive":
        if insight["routing_class"] == "A":
            return "alert_now"
        return "suppress"
    
    # Rule 2: Class A → always alert
    if insight["routing_class"] == "A":
        return "alert_now"
    
    # Rule 3: Class B → queue but mark high priority
    if insight["routing_class"] == "B":
        return "queue_report"  # with priority flag
    
    # Rule 4: Class C/D → queue for daily report
    return "queue_report"
```

**Silence Policy (from v3.2 Section 13.2):**
```python
def check_silence_policy(session_id: str) -> bool:
    """
    Returns True if Observer should go silent.
    - 3 consecutive insights user ignored in this session → silence
    - User explicitly asked to stop → silence for session
    """
```

### 4.5 Synthesis Composer (GPT API — Daily Report Only)

Called once per day (or on-demand), not per interaction.

**System Prompt:**

```
You are the Synthesis Composer for Next-Step AI. You produce a daily reflection report from accumulated insights.

## Input
A list of insights from today's interactions, each with:
- type (informational/inferential/complementary)
- content
- the original question it relates to
- routing class
- user reaction (if any)

## Output Structure
Produce a report in markdown with these sections:

### Key Findings Today
- Top 2-3 insights ranked by potential impact
- Each with one sentence of context

### Patterns Noticed
- Any recurring themes across today's interactions
- Only if genuinely recurring — don't force patterns from 2 data points

### Ready Questions
- 2-4 questions the user could ask next to go deeper
- These must be specific and actionable, not generic

### Quick Stats
- Interactions today: N
- Insights generated: N
- Insights engaged with: N
- Topics covered: [list]

## Rules
- Be concise — the entire report should be readable in 2 minutes
- Use the user's language (Arabic/English/mixed as appropriate)
- Never praise the user — this is a tool, not a companion
- Never repeat insights the user already engaged with in detail
- If nothing meaningful accumulated → say "No significant findings today" and skip the report
```

---

## 5. Orchestrator — The Flow

```python
async def handle_query(user_query: str, model_choice: str):
    """
    Main orchestration flow for each user interaction.
    """
    
    # Step 1: Collector classifies the query
    classification = collector.classify_query(user_query)
    
    # Step 2: Get base model response
    base_response = await call_base_model(user_query, model_choice)
    
    # Step 3: Display base response immediately to user
    yield base_response  # Streamlit streams this
    
    # Step 4: Store in raw memory
    session_id = get_current_session()
    memory.store_raw(user_query, base_response, session_id, model_choice)
    
    # Step 5: Extract canonical units
    memory.extract_canonical(user_query, base_response, session_id)
    
    # Step 6: Skip Insight for simple executive queries
    if classification["type"] == "executive" and classification["estimated_complexity"] == "simple":
        return
    
    # Step 7: Get relevant context from memory
    context = memory.get_relevant_context(user_query, limit=5)
    
    # Step 8: Call Insight Agent
    insight = await insight_agent.analyze(
        user_query, base_response, context, USER_PROFILE
    )
    
    # Step 9: If no insight → done
    if not insight["has_insight"]:
        return
    
    # Step 10: Route each angle
    for angle in insight["angles"]:
        action = observer.route_insight(angle, classification)
        
        if action == "alert_now":
            # Show immediately in UI
            yield {"type": "alert", "content": angle}
            memory.store_insight(angle, session_id, surfaced=True)
        
        elif action == "queue_report":
            memory.store_insight(angle, session_id, surfaced=False)
        
        # suppress → don't store
```

---

## 6. User Profile — Hardcoded for Phase 1

Instead of building maps dynamically, Phase 1 uses a static profile based on the founder's known cognitive map (from v3.2 Section 21.4).

```python
USER_PROFILE = """
## User Cognitive Profile

Strengths:
- Building conceptual frameworks and strategic thinking
- Detecting contradictions and structural weaknesses
- Thinking from frameworks down to details
- Understanding technology from a product perspective

Known Gaps:
- Direct programming implementation
- Resolving the boundary between ambition and execution scope

Hidden Assumptions to Watch:
- Tends to assume complete understanding is required before action
- Trusts analysis more than experimentation
- May over-document instead of testing

Communication Style:
- Mixes Arabic and English naturally
- Prefers framework-first explanations
- Values directness over cushioning
- Builds arguments from structure to details

Decision Pattern:
- Deliberate — needs the full picture before moving
- Strong pattern of conceptual framework-building before execution
"""
```

This profile is injected into the Insight Agent prompt. In Phase 2, it gets replaced by dynamically derived maps.

---

## 7. Project File Structure

```
nextstep-ai/
├── app.py                    # Streamlit entry point
├── config.py                 # API keys, model settings, constants
├── requirements.txt          # Python dependencies
├── database/
│   ├── schema.sql            # All CREATE TABLE statements
│   ├── db.py                 # SQLite connection and helpers
│   └── nextstep.db           # Created at runtime
├── agents/
│   ├── collector.py          # Query classification (rules)
│   ├── memory.py             # Storage and retrieval
│   ├── insight.py            # Missing angle generation (API)
│   ├── observer.py           # Routing logic (rules)
│   └── synthesis.py          # Report generation (API)
├── orchestrator.py           # Main flow coordination
├── prompts/
│   ├── insight_system.md     # Insight Agent system prompt
│   ├── insight_user.md       # Insight Agent user template
│   └── synthesis_system.md   # Synthesis Composer system prompt
├── reports/                  # Generated daily reports (markdown)
│   └── 2026-04-12.md
├── profiles/
│   └── founder.py            # Static user profile
└── tests/
    └── test_30_interactions.py  # Structured test framework
```

---

## 8. UI Specification (Streamlit)

### Page 1: Chat (Main)
- Model selector: dropdown (Claude / GPT)
- Text input area (supports Arabic + English)
- Response display area
- Alert box: appears only when Class A insight is routed
- Alert format: highlighted box with the missing angle + "Dismiss" / "Tell me more" buttons
- Session counter: "Interaction 7/30"

### Page 2: Daily Report
- Today's report (auto-generated or on-demand)
- Past reports list (by date)
- Each report shows: key findings, patterns, ready questions, stats

### Page 3: Memory Browser
- Search through past interactions
- View canonical units
- View all insights (with user reaction status)
- Simple stats: topics covered, insights generated, engagement rate

### Page 4: Settings
- API keys (Claude + OpenAI)
- Default model choice
- Observer sensitivity: "aggressive" | "balanced" | "conservative"
- Report generation: "auto-daily" | "manual"

---

## 9. Evaluation Framework — 30 Interactions Test

### What to Track Per Interaction
```json
{
    "interaction_id": 1,
    "query": "...",
    "query_type": "analytical",
    "model_used": "claude",
    "insight_generated": true,
    "insight_type": "informational",
    "routing_class": "C",
    "user_reaction": "engaged",
    "quality_score": 4,
    "notes": "Genuinely didn't know about this standard"
}
```

### Quality Score (1-5, self-rated)
- 1: Filler — obvious or irrelevant
- 2: Marginally useful — knew most of it
- 3: Useful — added a relevant angle
- 4: Valuable — changed my next question or approach
- 5: Critical — caught a blind spot that would have caused a real problem

### Success Criteria (from v3.2 Section 14)
- ≥60% of insights score 3+ (useful or better)
- ≥30% of insights score 4+ (changed thinking direction)
- ≤15% of insights score 1 (pure filler)
- ≥3 Class A alerts that were genuinely urgent
- User engagement rate with insights ≥50%

### Weekly Review Questions
- Am I asking better questions this week than last week?
- Did any insight prevent a real mistake?
- Did any insight feel annoying or patronizing?
- Is the system silent when it should be?

---

## 10. Dependencies

```txt
# requirements.txt
streamlit>=1.30.0
anthropic>=0.40.0
openai>=1.50.0
python-dotenv>=1.0.0
```

---

## 11. Setup Instructions

```bash
# 1. Create project
mkdir nextstep-ai && cd nextstep-ai

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install streamlit anthropic openai python-dotenv

# 4. Create .env file
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
echo "OPENAI_API_KEY=sk-..." >> .env

# 5. Initialize database
python database/db.py

# 6. Run
streamlit run app.py
```

---

## 12. What Phase 2 Adds (After 30 Interactions Prove Value)

- Graph Memory (Graphiti/Zep) replacing keyword-based retrieval
- Dynamic Cognitive Map built from accumulated interactions
- Delta Layer tracking changes between reports
- Calibration Agent for map drift correction
- Context Agent with graph-backed 500-800 token retrieval
- GEPA+DSPy research for automatic prompt optimization
- Behavioral and Personal maps
- Cold Start from external sources (LinkedIn/CV/GitHub)
