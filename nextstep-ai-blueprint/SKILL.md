# SKILL.md — How to Build Next-Step AI Phase 1

## Read First

Before writing ANY code, read these files in order:
1. `SOUL.md` — What the product is and isn't
2. `docs/ARCHITECTURE.md` — System design and agent contracts
3. `schemas/SCHEMAS.md` — All data structures
4. `prompts/PROMPTS.md` — All LLM prompts
5. `tests/TESTING.md` — What must pass before anything ships
6. `TASKS.md` — Step-by-step build order

## Tech Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| Language | Python 3.11+ | Ecosystem: Anthropic SDK, OpenAI SDK, Streamlit |
| UI | Streamlit | Simplest path to a working UI for non-technical user |
| Database | SQLite | Local-first, zero setup, sufficient for single user |
| LLM APIs | Anthropic (Claude) + OpenAI (GPT) | User chooses per query |
| Config | python-dotenv + .env file | API keys stay out of code |

## Dependencies (requirements.txt)

```
streamlit>=1.30.0
anthropic>=0.40.0
openai>=1.50.0
python-dotenv>=1.0.0
```

No other dependencies in Phase 1. No LangChain. No vector DB. No graph DB.
Keep it simple — complexity is Phase 2.

## Project Structure

```
nextstep-ai/
├── app.py                      # Streamlit entry point — 4 pages
├── config.py                   # Settings, API keys, constants
├── orchestrator.py             # Main flow: query → answer → insight → route
├── requirements.txt
├── .env                        # API keys (not committed)
├── .env.example                # Template for .env
│
├── agents/
│   ├── __init__.py
│   ├── collector.py            # Query classification (RULES ONLY — no LLM)
│   ├── memory.py               # SQLite storage + retrieval
│   ├── insight.py              # Missing angle generation (Claude API)
│   ├── observer.py             # Routing logic (RULES ONLY — no LLM)
│   └── synthesis.py            # Daily report generation (GPT API)
│
├── database/
│   ├── schema.sql              # All CREATE TABLE statements
│   └── db.py                   # Connection helper, init, migrations
│
├── prompts/
│   ├── insight_system.txt      # Insight Agent system prompt
│   ├── insight_user.txt        # Insight Agent user template
│   └── synthesis_system.txt    # Synthesis Composer system prompt
│
├── profiles/
│   └── founder.md              # Static user profile for Phase 1
│
├── reports/                    # Generated daily reports
│   └── .gitkeep
│
└── tests/
    ├── test_collector.py       # Unit tests for classification
    ├── test_observer.py        # Unit tests for routing logic
    ├── test_memory.py          # Unit tests for storage/retrieval
    ├── test_orchestrator.py    # Integration test for full flow
    └── test_insight_quality.py # Quality evaluation framework
```

## Coding Conventions

### General
- Type hints on all function signatures
- Docstrings on all public functions (one-line summary + Args + Returns)
- No classes unless necessary — prefer functions and simple data structures
- Use `dict` and `dataclass` for data, not ORM models
- All times in ISO 8601 UTC
- All IDs are UUID4 strings
- All text stored as UTF-8

### Error Handling
- Every API call wrapped in try/except with retry (max 2 retries, exponential backoff)
- If API fails → log error, skip insight for this interaction, continue
- If database fails → log error, alert user, do not lose the base model response
- NEVER crash the UI because an agent failed. The base answer must always display.

### API Calls
- Use `anthropic` SDK directly — not LangChain or wrappers
- Use `openai` SDK directly
- Model choices:
  - Insight Agent: `claude-sonnet-4-20250514` (best cost/quality for analysis)
  - Synthesis Composer: `gpt-4o` (good at structured report writing)
  - Base model: user's choice per query (Claude or GPT)
- All API calls must include:
  - `max_tokens` appropriate to task
  - `temperature=0.3` for Insight Agent (consistent analysis)
  - `temperature=0.5` for Synthesis (slightly more creative reports)
  - JSON mode where supported

### Streamlit Specifics
- Use `st.session_state` for session management
- Use `st.sidebar` for navigation between pages
- Use `st.chat_message` for the chat interface
- Use `st.expander` for insight alerts (collapsible)
- Use `st.metric` for report stats
- RTL support: add CSS for Arabic text direction
- Store session_id in st.session_state on first load

### Database
- Use `sqlite3` from stdlib — no ORM
- All queries parameterized (no string interpolation)
- WAL mode enabled for concurrent reads
- Database file: `database/nextstep.db`
- Init script runs on first launch (checks if tables exist)

## Agent Implementation Rules

### Which Agents Use LLM vs Rules

| Agent | Implementation | Why |
|-------|---------------|-----|
| Collector | Python rules only | Classification is deterministic |
| Memory | Python + SQLite only | Storage/retrieval is mechanical |
| Context | Python only | Prompt assembly is template work |
| Insight | Claude API call | Core value — needs reasoning |
| Observer Router | Python rules only | Routing is a decision tree |
| Synthesis | GPT API call | Report writing needs language skill |

### Critical: Agents Must Not Cross Boundaries

From SOUL.md and the vision document (v3.2 Section 10):
- Collector NEVER updates maps or decides what to surface
- Memory NEVER uses existing maps to filter what enters Raw
- Insight NEVER modifies maps or decides what to show the user
- Observer NEVER generates content — only routes
- Synthesis NEVER changes routing decisions

If you find yourself writing code where one agent does another's job → stop and refactor.

## Config Structure

```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Model Choices
INSIGHT_MODEL = "claude-sonnet-4-20250514"
SYNTHESIS_MODEL = "gpt-4o"
BASE_MODEL_OPTIONS = {
    "Claude": {"provider": "anthropic", "model": "claude-sonnet-4-20250514"},
    "GPT": {"provider": "openai", "model": "gpt-4o"},
}

# Observer Settings
OBSERVER_SENSITIVITY = "balanced"  # aggressive | balanced | conservative
MAX_INSIGHTS_PER_INTERACTION = 2
SILENCE_AFTER_IGNORES = 3
MAX_CONTEXT_TOKENS = 800

# Paths
DB_PATH = "database/nextstep.db"
REPORTS_DIR = "reports"
PROMPTS_DIR = "prompts"
PROFILES_DIR = "profiles"
```

## UI Pages Specification

### Page 1: Chat (Main)
- Top: model selector dropdown (Claude / GPT)
- Chat interface using st.chat_message
- User types message → base model responds → displayed immediately
- If Class A alert → st.expander appears below the answer with:
  - Alert icon + "⚠️ زاوية غائبة" / "⚠️ Missing Angle"
  - The insight content
  - Two buttons: "أخبرني أكثر" (Tell me more) / "تجاهل" (Dismiss)
  - User reaction stored in database
- Bottom: session counter "تفاعل 7/30"

### Page 2: Daily Report
- Button: "Generate Today's Report" (calls Synthesis Composer)
- Display area: rendered markdown
- Sidebar: list of past report dates (clickable)
- If no insights today → show "لا توجد نتائج مهمة اليوم"

### Page 3: Memory Browser
- Search box: keyword search through canonical_units
- Results list: each showing summary, type, date, topic tags
- Expandable: click to see full content + related insights
- Stats panel: total interactions, insights generated, engagement rate, top topics

### Page 4: Settings
- API key inputs (password fields)
- Default model selector
- Observer sensitivity slider
- Report frequency: auto-daily / manual
- Export data button (downloads SQLite file)
- Clear all data button (with confirmation)

### RTL Support
```css
/* Add to Streamlit custom CSS */
.rtl-text {
    direction: rtl;
    text-align: right;
    font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
}
```
Apply `.rtl-text` class when language detection returns "ar" or "mixed".

## Performance Targets

| Metric | Target |
|--------|--------|
| Base model response display | < 3 seconds (streaming) |
| Insight generation | < 5 seconds (background, after answer shown) |
| Memory storage | < 100ms |
| Context retrieval | < 200ms |
| Daily report generation | < 15 seconds |
| UI page load | < 2 seconds |

## What NOT to Build in Phase 1

DO NOT build any of these — they are Phase 2:
- Graph database / Graphiti / Zep integration
- Dynamic map generation (Cognitive, Behavioral, Personal)
- Delta Layer tracking
- Calibration Agent
- GEPA+DSPy prompt optimization
- Local model support (Ollama)
- External source ingestion (LinkedIn, CV, GitHub)
- Psychological state analysis
- Voice/audio layer (HVA)
- Fine-tuning of any kind
- User authentication (single user only)
- Cloud deployment
- Mobile interface
