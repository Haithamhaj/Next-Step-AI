import os
import json
import asyncio
from datetime import datetime, timezone

from config import PROFILES_DIR, REPORTS_DIR
from agents import memory, insight, synthesis
from agents import research
from agents import prompt_architect
from agents import context_agent
from agents import domain_ensemble
from agents import calibration
import database.db as db
from maps.map_builder import build_maps_context

async def analyze_and_report(lang: str = "ar") -> tuple:
    pending = memory.get_pending_conversations()
    if not pending:
        if lang == "ar":
            return "لا توجد محادثات قيد الانتظار للتحليل.", "", {}, {}, None
        return "No conversations pending analysis.", "", {}, {}, None

    # ── Load profile ──
    profile_path = os.path.join(PROFILES_DIR, "founder.md")
    if os.path.exists(profile_path):
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = f.read()
    else:
        profile = "No profile found."

    # ── Build maps context ──
    maps_context = build_maps_context(lang)

    # ── Context Agent: assemble focused context pack ──
    context_pack = context_agent.build_context_pack(
        conversations=pending,
        maps_context=maps_context or "",
        profile=profile,
        lang=lang,
    )

    conversations_block = context_pack["conversations_block"]
    profile_block = context_pack["profile_block"]
    maps_block = context_pack["maps_block"]
    topic_signals = context_pack["topic_signals"]
    context_stats = {
        "conversations_included": context_pack["conversations_included"],
        "conversations_truncated": context_pack["conversations_truncated"],
        "token_estimate": context_pack["token_estimate"],
    }

    # Combined profile for agents that need maps context
    if maps_block:
        combined_profile = profile_block + "\n\n" + maps_block
    else:
        combined_profile = profile_block

    # ── Research Agent: discover external tools/standards ──
    topic_summary = " | ".join(topic_signals) if topic_signals else conversations_block[:500]
    research_data = await asyncio.to_thread(
        research.research_topic, topic_summary, conversations_block, combined_profile, lang
    )
    discoveries = research_data.get("discoveries", [])

    # ── Domain Agent Ensemble: parallel specialized analysis ──
    ensemble_output = await asyncio.to_thread(
        domain_ensemble.run_ensemble,
        conversations_block, topic_signals, discoveries, maps_block, lang
    )

    # ── Insight Agent: analyze conversations ──
    analysis_data = await asyncio.to_thread(insight.analyze_conversations, conversations_block, combined_profile, lang, discoveries, ensemble_output)

    conv_ids = [c["id"] for c in pending]

    if analysis_data.get("error"):
        error_msg = analysis_data.get("skip_reason", "Unknown API error")
        return (
            f"⚠️ فشل تحليل {context_stats['conversations_included']} محادثة بسبب قيود Anthropic: "
            f"`{error_msg}`. يرجى الانتظار لمدة دقيقة ثم المحاولة مجدداً.", "", {}, {}, None, None
        )

    all_findings = analysis_data.get("findings", [])
    session_summary = analysis_data.get("session_summary", "")

    # Mark ALL analyzed conversations as done AFTER the single successful call
    for conv in pending:
        memory.mark_analyzed(conv["id"])

    # ── Prompt Architect: build ready_prompts for all findings ──
    classified = {"completion": [], "alignment": [], "contradiction": []}
    type_map = {
        "informational": "completion",
        "complementary": "alignment",
        "inferential": "contradiction",
    }
    for finding in all_findings:
        category = type_map.get(finding.get("type", ""), "completion")
        classified[category].append(finding)

    enriched_classified = await asyncio.to_thread(
        prompt_architect.build_prompts,
        classified, conversations_block, maps_block, lang
    )

    # Flatten classified findings back into a single list for synthesis
    all_findings_with_prompts = []
    for category in ("completion", "alignment", "contradiction"):
        all_findings_with_prompts.extend(enriched_classified.get(category, []))

    unified_analysis = {
        "session_summary": session_summary,
        "findings": all_findings_with_prompts,
        "has_insight": bool(all_findings_with_prompts)
    }

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    report_content = synthesis.generate_report(unified_analysis, date_str, lang)

    stats = {
        "insights_count": len(all_findings_with_prompts),
        "sessions_count": context_stats["conversations_included"],
    }

    report_id = memory.store_report(date_str, report_content, stats)

    # ── Generate Contextual Instructions ──
    import uuid
    contextual_instructions = synthesis.generate_contextual_instructions(
        unified_analysis, combined_profile, lang, session_summary
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

    # ── Store Domain Ensemble Results ──
    if ensemble_output and ensemble_output.get("agent_count", 0) > 0:
        db.insert_ensemble_result(
            str(uuid.uuid4()), report_id,
            ensemble_output.get("domains_identified", []),
            ensemble_output.get("agent_count", 0),
            ensemble_output.get("completion_findings", []),
            ensemble_output.get("alignment_findings", []),
            ensemble_output.get("contradiction_findings", [])
        )

    # ── Store insights with conversation IDs ──
    for finding in all_findings_with_prompts:
        memory.store_insight(finding, report_id, conv_ids)

    # ── Calibration Agent: audit existing insights against new evidence ──
    calibration_results = calibration.run_calibration(
        new_findings=all_findings_with_prompts,
        existing_insights=db.get_insights_for_calibration(),
        maps_context=maps_block or "",
        lang=lang,
    )

    # Apply calibration actions
    for item in calibration_results.get("weakened", []):
        action = item.get("action", "flag")
        action_map = {"weaken": "weakened", "flag": "flagged", "request_confirmation": "pending_confirmation"}
        db.update_insight_calibration_status(
            item["insight_id"], action_map.get(action, "flagged")
        )

    db.insert_calibration_log(
        report_id,
        calibration_results.get("insights_reviewed", 0),
        calibration_results.get("insights_weakened", 0),
        calibration_results.get("calibration_summary", ""),
        calibration_results.get("weakened", []),
        calibration_results.get("stale_map_inputs", []),
    )

    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(os.path.join(REPORTS_DIR, f"report_{date_str}.md"), "w", encoding="utf-8") as f:
        f.write(report_content)

    return report_content, contextual_instructions, research_data, context_stats, calibration_results, report_id
