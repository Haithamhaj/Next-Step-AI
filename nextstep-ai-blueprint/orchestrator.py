import os
import json
import asyncio
from datetime import datetime, timezone

from config import PROFILES_DIR, REPORTS_DIR
from agents import memory, insight, synthesis
from agents import research
import database.db as db

async def analyze_and_report(lang: str = "ar") -> tuple:
    pending = memory.get_pending_conversations()
    if not pending:
        if lang == "ar":
            return "لا توجد محادثات قيد الانتظار للتحليل.", "", {}
        return "No conversations pending analysis.", "", {}

    profile_path = os.path.join(PROFILES_DIR, "founder.md")
    if os.path.exists(profile_path):
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = f.read()
    else:
        profile = "No profile found."

    # ── FIX 1: Build ONE combined context block from ALL conversations ──
    # Truncate oldest conversations first if combined block exceeds 20k chars.
    HARD_CAP = 20000

    # Sort oldest → newest (already ordered by added_at ASC from db)
    convs_for_analysis = []
    for conv in pending:
        text = conv.get('compressed_content') or conv['content']
        c = dict(conv)
        c['_analysis_text'] = text
        convs_for_analysis.append(c)

    # Build full combined block and truncate from the oldest if needed
    def build_combined(convs):
        block = ""
        for c in convs:
            block += f"=== Conversation: {c['label']} (Source: {c['source']}) ===\n"
            block += f"{c['_analysis_text']}\n\n"
        return block

    combined = build_combined(convs_for_analysis)
    if len(combined) > HARD_CAP:
        # Drop oldest conversations until we fit; always keep at least the newest one
        while len(combined) > HARD_CAP and len(convs_for_analysis) > 1:
            convs_for_analysis.pop(0)  # remove oldest
            combined = build_combined(convs_for_analysis)
        # If a single conversation still exceeds cap, truncate its text directly
        if len(combined) > HARD_CAP:
            c = convs_for_analysis[0]
            c['_analysis_text'] = c['_analysis_text'][:HARD_CAP] + \
                "\n\n...[TRUNCATED — conversation too large even after compression]"
            combined = build_combined(convs_for_analysis)

    # ── Research Agent: discover external tools/standards before insight ──
    topic_summary_raw = combined[:500]
    research_data = await asyncio.to_thread(
        research.research_topic, topic_summary_raw, combined, profile, lang
    )
    discoveries = research_data.get("discoveries", [])

    # ── FIX 1: Call insight agent ONCE with the full combined block ──
    analysis_data = await asyncio.to_thread(insight.analyze_conversations, combined, profile, lang, discoveries)

    conv_ids = [c["id"] for c in convs_for_analysis]

    if analysis_data.get("error"):
        error_msg = analysis_data.get("skip_reason", "Unknown API error")
        return (
            f"⚠️ فشل تحليل {len(convs_for_analysis)} محادثة بسبب قيود Anthropic: "
            f"`{error_msg}`. يرجى الانتظار لمدة دقيقة ثم المحاولة مجدداً."
        ), "", {}

    all_findings = analysis_data.get("findings", [])
    session_summary = analysis_data.get("session_summary", "")

    # Mark ALL analyzed conversations as done AFTER the single successful call
    for conv in convs_for_analysis:
        memory.mark_analyzed(conv["id"])

    # canonical_units insertion removed —
    # to be reimplemented when Context Agent is built (Priority 7)

    unified_analysis = {
        "session_summary": session_summary,
        "findings": all_findings,
        "has_insight": bool(all_findings)
    }

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    report_content = synthesis.generate_report(unified_analysis, date_str, lang)

    stats = {
        "insights_count": len(all_findings),
        "sessions_count": len(convs_for_analysis),
    }

    report_id = memory.store_report(date_str, report_content, stats)

    # ── Generate Contextual Instructions ──
    import uuid
    contextual_instructions = synthesis.generate_contextual_instructions(
        unified_analysis, profile, lang, session_summary
    )
    instruction_id = db.insert_contextual_instruction(
        str(uuid.uuid4()), report_id, contextual_instructions, session_summary, lang
    )

    # ── Store Research Results ──
    db.insert_research_result(
        str(uuid.uuid4()), report_id,
        session_summary,
        discoveries,
        research_data.get("search_queries_used", []),
        research_data.get("research_summary", "")
    )

    # ── FIX 3: Pass conversation IDs to every stored insight ──
    for finding in all_findings:
        memory.store_insight(finding, report_id, conv_ids)

    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(os.path.join(REPORTS_DIR, f"report_{date_str}.md"), "w", encoding="utf-8") as f:
        f.write(report_content)

    return report_content, contextual_instructions, research_data
