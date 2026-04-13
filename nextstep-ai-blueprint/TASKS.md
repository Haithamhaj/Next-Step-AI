# TASKS.md — Build Order

## Critical Rule for the Building Agent

Read SOUL.md, SKILL.md, docs/ARCHITECTURE.md, schemas/SCHEMAS.md, prompts/PROMPTS.md, and tests/TESTING.md BEFORE writing any code.

Build in this exact order. Do NOT skip ahead. Each task has a verification step — pass it before moving on.

---

## Phase 0: Project Setup

### Task 0.1: Initialize Project
```
- Create folder structure as specified in SKILL.md
- Create requirements.txt
- Create .env.example with placeholder keys
- Create config.py with all settings from SKILL.md
```
**Verify:** `python config.py` runs without error.

### Task 0.2: Database Setup
```
- Create database/schema.sql from SCHEMAS.md
- Create database/db.py with:
  - init_db() — creates tables if not exist
  - get_connection() — returns sqlite3 connection with WAL mode
  - Helper functions: insert_raw, insert_canonical, insert_insight, insert_session, insert_report
  - Query functions: get_raw_by_session, get_canonical_by_tags, get_insights_by_date, get_queued_insights
```
**Verify:** Run `python database/db.py` → creates nextstep.db with all tables. Query tables — all exist and empty.

### Task 0.3: Create Prompt Files
```
- Create prompts/insight_system.txt (from PROMPTS.md Section 1)
- Create prompts/insight_user.txt (from PROMPTS.md Section 2)
- Create prompts/synthesis_system.txt (from PROMPTS.md Section 3)
```
**Verify:** All three files exist and contain the full prompts.

### Task 0.4: Create Profile
```
- Create profiles/founder.md (from profiles section below — copy as-is)
```
**Verify:** File exists and is readable.

---

## Phase 1: Build Agents (Bottom-Up)

### Task 1.1: Collector Agent
```
File: agents/collector.py

Implement:
- classify_query(query: str) -> dict
- Language detection (Arabic char ratio)
- Type classification (keyword matching with lists)
- Complexity estimation (word count + keyword analysis)

Keyword lists for classification:
- executive: [translate, ترجم, format, fix, أصلح, send, أرسل, write email, draft, اكتب]
- decision: [should I, هل أستخدم, which is better, أيهم أفضل, compare, قارن, choose, decide]
- analytical: [why, لماذا, how does, كيف, explain, اشرح, analyze, حلل, what causes]
- exploration: [what if, ماذا لو, imagine, تخيل, explore, brainstorm]
- creative: [design, صمم, create, أنشئ, build, ابني, make, اصنع]
- Default (no match): "exploration"
```
**Verify:** Run test_collector.py — all tests pass.

### Task 1.2: Memory Agent
```
File: agents/memory.py

Implement:
- store_interaction(query, response, session_id, model_used, classification) -> tuple(raw_ids, canonical_ids)
- extract_canonical_units(query, response, classification) -> list[dict]
- extract_topic_tags(text) -> list[str]
- get_relevant_context(query, limit=5) -> list[dict]
- build_context_block(units, max_chars=3200) -> str
- store_insight(insight_data, session_id, surfaced) -> str
- get_queued_insights(date) -> list[dict]
- store_report(date, content, stats) -> str
- get_session_ignore_count(session_id) -> int
- record_user_reaction(insight_id, reaction) -> None
```
**Verify:** Run test_memory.py — all tests pass. Manually insert 5 interactions, retrieve context — returns relevant results.

### Task 1.3: Insight Agent
```
File: agents/insight.py

Implement:
- analyze(query, response, context_block, profile) -> dict
  - Loads system prompt from prompts/insight_system.txt
  - Formats user prompt from prompts/insight_user.txt
  - Calls Claude API (claude-sonnet-4-20250514)
  - temperature=0.3, max_tokens=1000
  - Parses JSON response
  - Validates output structure (has_insight, angles array, etc.)
  - Retries once on parse failure
  - Returns {"has_insight": false, "angles": [], "skip_reason": "API error"} on failure

API call pattern:
  client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
  response = client.messages.create(
      model=INSIGHT_MODEL,
      max_tokens=1000,
      temperature=0.3,
      system=system_prompt,
      messages=[{"role": "user", "content": user_prompt}]
  )
```
**Verify:** Call with a test query + response → returns valid JSON with correct structure. Call with a purely executive query → returns has_insight=false.

### Task 1.4: Observer Router
```
File: agents/observer.py

Implement:
- route_insight(insight_angle, classification, session_id) -> str
  - Returns: "alert_now" | "queue_report" | "suppress"
  - Decision tree from ARCHITECTURE.md
- check_silence_policy(session_id) -> bool
  - Queries memory for ignore count in session
  - Returns True if >= 3 consecutive ignores
```
**Verify:** Run test_observer.py — all tests pass.

### Task 1.5: Synthesis Composer
```
File: agents/synthesis.py

Implement:
- compose_daily_report(insights, date) -> str
  - Loads system prompt from prompts/synthesis_system.txt
  - Formats insights as structured input
  - Calls GPT API (gpt-4o)
  - temperature=0.5, max_tokens=2000
  - Returns markdown string
  - On failure → returns formatted list of raw insights as fallback
```
**Verify:** Call with 5 test insights → returns valid markdown report with all sections.

---

## Phase 2: Build Orchestrator

### Task 2.1: Orchestrator
```
File: orchestrator.py

Implement:
- handle_interaction(query, model_choice) -> dict
  - Full flow from ARCHITECTURE.md
  - Returns: {"answer": str, "alert": dict|None, "classification": dict}
  
- generate_daily_report(date) -> str
  - Fetches queued insights
  - Calls Synthesis Composer
  - Stores report
  - Returns markdown

- get_or_create_session() -> str
  - Creates new session if none active
  - Returns session_id

- Base model call function:
  - If model_choice == "Claude": use Anthropic API
  - If model_choice == "GPT": use OpenAI API
  - Streaming support for Streamlit
```
**Verify:** Full integration test — send a query, get answer + insight + routing decision. Verify all data stored in SQLite correctly.

---

## Phase 3: Build UI

### Task 3.1: Streamlit App — Chat Page
```
File: app.py

Page 1 — Chat:
- Sidebar: page navigation (Chat / Report / Memory / Settings)
- Top: model selector dropdown
- Chat interface with st.chat_message
- Message input at bottom
- When user sends message:
  1. Show "thinking..." for base model
  2. Stream base model response
  3. Run insight pipeline in background
  4. If Class A alert → show expandable alert box below answer
  5. Alert has: content + "أخبرني أكثر" button + "تجاهل" button
  6. Button clicks → store user_reaction in database
- Bottom: "تفاعل N/30" counter
- RTL CSS support for Arabic text
```
**Verify:** Open in browser. Type a question. Get answer. Alert appears for test Class A insight.

### Task 3.2: Streamlit App — Report Page
```
Page 2 — Daily Report:
- "إنشاء تقرير اليوم" button
- Loading spinner while generating
- Rendered markdown report
- Sidebar: list of past report dates
- Click date → show that report
- If no insights → show "لا توجد نتائج مهمة اليوم"
```
**Verify:** Generate a report after 3+ interactions. Report renders correctly with all sections.

### Task 3.3: Streamlit App — Memory Browser
```
Page 3 — Memory:
- Search input box
- Results: list of canonical units matching search
- Each result shows: date, type badge, summary, topic tags
- Expandable: full content + related insights
- Stats panel at top: total interactions, insights count, engagement rate, top 5 topics
```
**Verify:** Search returns relevant results. Stats are accurate.

### Task 3.4: Streamlit App — Settings
```
Page 4 — Settings:
- API key inputs (st.text_input with type="password")
- Default model selector
- Observer sensitivity: st.select_slider (conservative/balanced/aggressive)
- Report mode: auto-daily / manual
- "Export Database" button → downloads nextstep.db
- "Clear All Data" button → st.warning confirmation → resets database
- "Save" button → updates config
```
**Verify:** Change settings. Restart app. Settings persist.

---

## Phase 4: Testing

### Task 4.1: Run All Unit Tests
```
python -m pytest tests/test_collector.py -v
python -m pytest tests/test_observer.py -v
python -m pytest tests/test_memory.py -v
python -m pytest tests/test_orchestrator.py -v
```
**All must pass before proceeding.**

### Task 4.2: Create Evaluation Tracker
```
Create tests/evaluation_tracker.json with template structure.
Create a simple Streamlit page or script to log quality scores after each interaction.
Or: add a quality scoring widget to the Chat page (1-5 star rating below each insight).
```

### Task 4.3: Smoke Test — 5 Real Interactions
```
Before the full 30-interaction test, run 5 diverse queries:
1. Executive query (translation/formatting) → verify Observer stays silent
2. Decision query → verify insight generated and routed correctly
3. Analytical query → verify insight quality
4. Arabic-only query → verify language handling
5. Query related to a previous one → verify context retrieval works
```

---

## Phase 5: The 30-Interaction Test

The user (founder) runs 30 real interactions from daily work.
Rate each insight. Log reactions. Generate daily reports.
After 30: evaluate against success criteria in TESTING.md.

This phase is human-driven, not automated.

---

## Summary: Total Estimated Effort

| Phase | Tasks | Estimated Time |
|-------|-------|---------------|
| Phase 0: Setup | 4 tasks | 2-3 hours |
| Phase 1: Agents | 5 tasks | 4-6 hours |
| Phase 2: Orchestrator | 1 task | 2-3 hours |
| Phase 3: UI | 4 tasks | 3-4 hours |
| Phase 4: Testing | 3 tasks | 2-3 hours |
| **Total build** | **17 tasks** | **13-19 hours** |
| Phase 5: Evaluation | 30 interactions | 1-2 weeks of normal use |
