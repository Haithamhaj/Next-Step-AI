# TESTING.md — Testing & Evaluation Framework

## Two Types of Testing

1. **Unit Tests** — Does each agent work correctly in isolation?
2. **Quality Evaluation** — Does Observer generate genuinely useful insights?

Both must pass. Unit tests are automated. Quality evaluation is human-rated.

---

## Part 1: Unit Tests

### test_collector.py

Test the classification logic with specific cases:

```python
# Executive queries → type="executive"
assert classify("ترجم هذا النص")["type"] == "executive"
assert classify("Format this as a table")["type"] == "executive"
assert classify("أرسل هذا الإيميل")["type"] == "executive"

# Decision queries → type="decision"
assert classify("هل أستخدم React أو Vue؟")["type"] == "decision"
assert classify("Should I go with Claude or GPT?")["type"] == "decision"
assert classify("أيهم أفضل — اشتراك شهري أو سنوي؟")["type"] == "decision"

# Analytical queries → type="analytical"
assert classify("لماذا فشل هذا المشروع؟")["type"] == "analytical"
assert classify("How does RAG retrieval work?")["type"] == "analytical"

# Language detection
assert classify("ترجم هذا النص")["language"] == "ar"
assert classify("Format this table")["language"] == "en"
assert classify("أريد أبني coaching tool")["language"] == "mixed"

# Complexity
assert classify("ترجم 'hello'")["estimated_complexity"] == "simple"
assert classify("حلل لي الفرق بين ثلاث استراتيجيات تسعير مع أمثلة من السوق السعودي")["estimated_complexity"] == "complex"

# Edge cases
assert classify("")["type"] == "exploration"  # empty → default
assert classify("مرحبا")["estimated_complexity"] == "simple"
```

### test_observer.py

Test the routing decision tree:

```python
# Class A always alerts
assert route({"routing_class": "A"}, {"type": "analytical"}) == "alert_now"
assert route({"routing_class": "A"}, {"type": "executive"}) == "alert_now"

# Executive + non-A → suppress
assert route({"routing_class": "B"}, {"type": "executive"}) == "suppress"
assert route({"routing_class": "C"}, {"type": "executive"}) == "suppress"

# Non-executive + B/C/D → queue
assert route({"routing_class": "B"}, {"type": "analytical"}) == "queue_report"
assert route({"routing_class": "C"}, {"type": "decision"}) == "queue_report"
assert route({"routing_class": "D"}, {"type": "exploration"}) == "queue_report"

# Silence policy
assert check_silence(session_with_3_ignores) == True
assert check_silence(session_with_2_ignores) == False
assert check_silence(new_session) == False
```

### test_memory.py

```python
# Storage
store_raw("test query", "test response", "sess_1", "claude")
result = get_raw_by_session("sess_1")
assert len(result) == 2  # query + response

# Canonical extraction
units = extract_canonical("Should I use React?", "Here's a comparison...", {"type": "decision"})
assert any(u["unit_type"] == "decision" for u in units)

# Topic tagging
tags = extract_topic_tags("I want to build a coaching tool with ICF standards")
assert "coaching" in tags

# Retrieval
store_multiple_interactions(...)  # seed 10 interactions
context = get_relevant_context("coaching tool", limit=5)
assert len(context) <= 5
assert all("coaching" in c.get("topic_tags", []) for c in context)

# Context token limit
block = build_context_block(context, max_chars=3200)
assert len(block) <= 3200
```

### test_orchestrator.py (Integration)

```python
# Full flow — happy path
result = await handle_interaction("أريد أبني أداة كوتشينج", "claude")
assert "answer" in result
assert result["answer"] is not None
assert result["answer"] != ""

# Executive query → no insight
result = await handle_interaction("ترجم 'hello world' للعربي", "gpt")
assert result["alert"] is None

# API failure → graceful degradation
with mock_api_failure("anthropic"):
    result = await handle_interaction("How does RAG work?", "claude")
    # Should still return answer from base model if that didn't fail
    # Insight simply missing — no crash

# Silence policy integration
for i in range(3):
    result = await handle_interaction(f"test query {i}", "claude")
    if result["alert"]:
        mark_reaction(result["alert"]["id"], "ignored")
# After 3 ignores:
result = await handle_interaction("another query", "claude")
assert result["alert"] is None  # Observer should be silent
```

---

## Part 2: Quality Evaluation — The 30 Interactions Test

### Setup

Create a spreadsheet or JSON file to track each of the 30 interactions:

```json
{
    "interaction_id": 1,
    "date": "2026-04-15",
    "query": "أريد أبني أداة كوتشينج لتقييم الجلسات",
    "query_type": "creative",
    "model_used": "claude",
    "base_answer_quality": 4,
    "insight_generated": true,
    "insight_type": "informational",
    "insight_content": "هناك معايير ICF محددة للكفاءات...",
    "routing_class": "C",
    "routing_action": "queue_report",
    "user_reaction": "engaged",
    "quality_score": 4,
    "changed_next_question": true,
    "notes": "لم أكن أعرف عن ICF — غيّرت اتجاه البحث"
}
```

### Quality Score Scale (Self-Rated)

| Score | Meaning | Example |
|-------|---------|---------|
| 1 | **Filler** — obvious, irrelevant, or repeated | "You might want to consider user needs" |
| 2 | **Marginal** — somewhat relevant but I mostly knew it | "Testing is important for this project" |
| 3 | **Useful** — added a relevant angle I hadn't focused on | "This standard exists in your domain" |
| 4 | **Valuable** — changed my next question or approach | "This contradicts what you decided last week" |
| 5 | **Critical** — caught a blind spot that could have caused real harm | "Your budget calculation has a fundamental error" |

### Success Criteria

| Metric | Target | How to Calculate |
|--------|--------|-----------------|
| Useful rate | ≥60% score 3+ | Count(score≥3) / Count(all scored insights) |
| Valuable rate | ≥30% score 4+ | Count(score≥4) / Count(all scored insights) |
| Filler rate | ≤15% score 1 | Count(score=1) / Count(all scored insights) |
| Skip accuracy | ≥80% correct skips | When Observer was silent, was it right to be? |
| Alert accuracy | ≥70% Class A justified | Of Class A alerts, how many were genuinely urgent? |
| Direction change | ≥40% | Count(changed_next_question=true) / Count(insights shown) |
| Engagement rate | ≥50% | Count(reaction != 'ignored') / Count(surfaced insights) |

### Daily Self-Check Questions

Ask yourself at end of each day during the 30-interaction test:

1. Did any insight today prevent a real mistake? (Y/N + which one)
2. Did any insight feel annoying or patronizing? (Y/N + which one)
3. Was the system silent when it should have spoken? (Y/N + describe)
4. Was the system noisy when it should have been silent? (Y/N + describe)
5. Did the daily report tell me something I didn't already know? (Y/N)
6. Am I asking better questions today than yesterday? (Y/N + evidence)

### Weekly Review Questions

After every 10 interactions:

1. Overall: is the system making me think differently? How?
2. Which insight type is most valuable? (informational / inferential / complementary)
3. Which routing class is most accurate? (A/B/C/D)
4. Is the daily report format useful or should it change?
5. Am I becoming dependent on the system or more independent?
6. What's the single biggest improvement the system needs?

### Failure Signals — Stop and Reassess If:

- Filler rate exceeds 30% after 15 interactions
- No score 4+ insight in the first 10 interactions
- User stops reading daily reports after week 1
- More than 3 false Class A alerts in 30 interactions
- User feels irritated more than informed

### What to Do with Results

**If targets are met:**
→ Phase 1 hypothesis proven. Proceed to Phase 2 (Graph Memory, dynamic maps).

**If partially met (some targets hit, others missed):**
→ Analyze which agent is weak. Likely: refine Insight Agent prompt, adjust Observer routing thresholds.
→ Run another 15 interactions with refined system.

**If clearly failed:**
→ The hypothesis may be wrong. Before abandoning:
  - Check if the Insight Agent prompt is too conservative or too aggressive
  - Check if the user profile is accurate enough
  - Check if the base model's answers are too comprehensive (leaving nothing to add)
  - Try switching the Insight Agent model
→ If still failing after adjustments → the concept needs fundamental rethinking.

---

## Part 3: Automated Quality Checks

### insight_quality_check.py

Run periodically to catch systematic issues:

```python
def check_insight_quality(db_path: str):
    """
    Automated checks on accumulated insights.
    """
    insights = get_all_insights(db_path)
    
    # Check 1: Filler accumulation
    scored = [i for i in insights if i["quality_score"] is not None]
    if scored:
        filler_rate = len([i for i in scored if i["quality_score"] == 1]) / len(scored)
        if filler_rate > 0.20:
            print(f"⚠️ WARNING: Filler rate is {filler_rate:.0%} — above 20% threshold")
    
    # Check 2: Routing accuracy
    class_a = [i for i in insights if i["routing_class"] == "A"]
    class_a_justified = [i for i in class_a if i["quality_score"] and i["quality_score"] >= 4]
    if class_a:
        accuracy = len(class_a_justified) / len(class_a)
        if accuracy < 0.70:
            print(f"⚠️ WARNING: Class A accuracy is {accuracy:.0%} — below 70%")
    
    # Check 3: Engagement trend
    recent = insights[-10:]  # last 10
    engaged = [i for i in recent if i["user_reaction"] in ("engaged", "asked_more")]
    if len(recent) > 0:
        rate = len(engaged) / len(recent)
        if rate < 0.40:
            print(f"⚠️ WARNING: Recent engagement rate is {rate:.0%} — below 40%")
    
    # Check 4: Type distribution
    types = [i["insight_type"] for i in insights]
    for t in ["informational", "inferential", "complementary"]:
        count = types.count(t)
        print(f"  {t}: {count} ({count/len(types):.0%})")
    
    # Check 5: Silence accuracy (require manual review log)
    print("\n📋 Manual review needed: Were there moments the system was silent but shouldn't have been?")
```
