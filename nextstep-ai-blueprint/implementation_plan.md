# Architectural Redesign: Conversation Review Layer

This plan outlines the steps required to transition Next-Step AI from a real-time chatbot interface into an asynchronous conversation review and analysis layer.

## Goal Description
The current implementation evaluates single queries on the fly. The new architecture will shift to bulk-importing external conversations (from Claude, GPT, Gemini) into the database as records, waiting for the user to trigger a batch analysis. 

The `Collector` and `Observer` logic along with live Chatbot UI will be dropped in favor of a deeper `Insight` parsing block (`prompts/insight_session_system.txt`) which evaluates cross-conversation dimensions and produces unified Daily Reports.

## Proposed Changes

---

### Database Layer
#### [MODIFY] `database/schema.sql`
- **[DELETE]** `raw_memory` and `sessions` tables.
- **[NEW]** `conversations` table (id, label, source, content, added_at, word_count, status, analyzed_at).
- **[MODIFY]** `canonical_units` to link to `conversation_id` instead of `session_id`.
- **[MODIFY]** `insights` to drop old routing mechanics and add `conversation_id`, `impact`,  `quality_score`, `conversations_referenced`.

#### [MODIFY] `database/db.py`
- Rewrite helper functions (`add_conversation`, `get_pending_conversations`, `mark_analyzed`, `insert_insight` adapted format, `get_conversations` list fetchers).

---

### Agents Layer
#### [DELETE] `agents/collector.py` & `agents/observer.py`
- Remove files completely as interaction routing is no longer applicable.

#### [NEW] `prompts/insight_session_system.txt` & `prompts/insight_session_user.txt`
- Create the cross-conversation batch analysis prompts enforcing strict JSON output structures.
#### [DELETE] `prompts/insight_system.txt` & `prompts/insight_user.txt`

#### [MODIFY] `agents/insight.py`
- Rename the analysis function to `analyze_conversations(conversations_list, profile)`.
- Use the new session prompts to bulk-evaluate pending conversations sequentially or simultaneously, generating the unified JSON output.

#### [MODIFY] `agents/synthesis.py`
- Refactor the Daily Report generation schema.
- Specifically FIX the OpenAI `gpt-4o` completion call implementation to ensure no silent exceptions or fallback failures occur during actual runs.

#### [MODIFY] `agents/memory.py`
- Implement topic tag expansion (e.g., observer, database, performance, latency).
- Expose `add_conversation`, `get_pending_conversations`, `mark_analyzed`. 

---

### Orchestrator Layer
#### [MODIFY] `orchestrator.py`
- Establish the `analyze_and_report()` control flow:
    1. Fetch pending conversations.
    2. Pass block to `insight.analyze_conversations`.
    3. Pass resulting angular insights to `synthesis.generate_report`.
    4. Store into database, update `conversations.status = 'analyzed'`.
    5. Return the full structured markdown report along with findings.

---

### UI Layer
#### [MODIFY] `app.py`
- **Page 1 (Add Conversations)**: Text area pasting + file upload (.txt, .md, .json) → Stores into DB (`pending`).
- **Page 2 (Analysis & Report)**: Lists pending conversations. "Analyze" button maps to `orchestrator.analyze_and_report()`. UI loading states and report visualization.
- **Page 3 (Insights Browser)**: Advanced grid reading all parsed `insights` records, enabling 1-5 star quality grading interactions.
- **Page 4 (Settings)**: Export DB, Clear DB, modify global variables.

---

### Testing Layer
#### [DELETE] `tests/test_collector.py` & `tests/test_observer.py`
#### [MODIFY] `tests/test_memory.py` & `tests/test_orchestrator.py`
- Build new isolated tests guaranteeing `add_conversation`, `get_pending`, and async analysis workflows.
#### [NEW] `live_smoke_new.py`
- Write an end-to-end execution script mocking the paste-and-analyze action with live logic directly reporting prompt traces to the console exactly as requested.

## Verification Plan

### Automated Tests
Execute `pytest` to assert component logic successfully captures data structures.

### Manual Verification
Execute `live_smoke_new.py` to provide a full transparent log of:
- Insertions of 2 simultaneous conversations into SQLite.
- Insight agent correctly parsing the string block combining both objects.
- Report successfully formatted using real OpenAI API and storing correctly without exceptions.
