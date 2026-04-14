import streamlit as st
import asyncio
import os
import glob

from config import DB_PATH, REPORTS_DIR, INSIGHT_MODEL, SYNTHESIS_MODEL
from agents.compressor import COMPRESSOR_MODEL
import database.db as db
from orchestrator import analyze_and_report
import agents.memory as memory
from i18n import t
from maps.map_builder import build_maps_context

st.set_page_config(
    page_title="Next-Step AI",
    page_icon="🔍",
    layout="wide"
)

# ── Init ──────────────────────────────────────────────────────
if "init" not in st.session_state:
    db.init_db()
    st.session_state.init = True

if "lang" not in st.session_state:
    st.session_state.lang = "ar"

lang = st.session_state.lang
is_rtl = lang == "ar"

# ── Global CSS ────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@300;400;500;600&family=Inter:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {{
    font-family: {"'IBM Plex Sans Arabic', 'Inter'" if is_rtl else "'Inter', 'IBM Plex Sans Arabic'"}, sans-serif;
    direction: {'rtl' if is_rtl else 'ltr'};
}}

/* Sidebar */
section[data-testid="stSidebar"] {{
    background: #0f1117;
    border-right: {'none' if is_rtl else '1px solid #1e2130'};
    border-left: {'1px solid #1e2130' if is_rtl else 'none'};
}}

/* Cards */
.conv-row {{
    display: flex;
    align-items: center;
    padding: 10px 14px;
    border-radius: 8px;
    background: #1a1d27;
    margin-bottom: 6px;
    gap: 12px;
}}

/* Status badges */
.badge-pending {{
    background: #2d1b00;
    color: #f59e0b;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 12px;
    white-space: nowrap;
}}
.badge-analyzed {{
    background: #052e16;
    color: #22c55e;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 12px;
    white-space: nowrap;
}}

/* Insight type chips */
.chip-informational {{ background: #1e3a5f; color: #60a5fa; padding: 2px 8px; border-radius: 12px; font-size: 12px; }}
.chip-inferential   {{ background: #3b1f5e; color: #c084fc; padding: 2px 8px; border-radius: 12px; font-size: 12px; }}
.chip-complementary {{ background: #1a3a2a; color: #4ade80; padding: 2px 8px; border-radius: 12px; font-size: 12px; }}
.chip-pattern       {{ background: #3a2a00; color: #fbbf24; padding: 2px 8px; border-radius: 12px; font-size: 12px; }}
.chip-high   {{ background: #3b0000; color: #f87171; padding: 2px 8px; border-radius: 12px; font-size: 11px; }}
.chip-medium {{ background: #2a1800; color: #fb923c; padding: 2px 8px; border-radius: 12px; font-size: 11px; }}
.chip-low    {{ background: #1a2a00; color: #a3e635; padding: 2px 8px; border-radius: 12px; font-size: 11px; }}

/* Compression stat */
.comp-stat {{
    font-size: 12px;
    color: #6ee7b7;
    background: #052e16;
    padding: 4px 10px;
    border-radius: 6px;
    display: inline-block;
    margin-top: 6px;
}}

/* Calibration badges */
.badge-flagged {{ background: #2d1b00; color: #f59e0b; padding: 2px 8px; border-radius: 12px; font-size: 12px; white-space: nowrap; }}
.badge-pending {{ background: #3b1500; color: #fb923c; padding: 2px 8px; border-radius: 12px; font-size: 12px; white-space: nowrap; }}
.badge-weakened {{ background: #1e2130; color: #6b7280; padding: 2px 8px; border-radius: 12px; font-size: 12px; white-space: nowrap; }}
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    # Language toggle at top
    col_ar, col_en = st.columns(2)
    with col_ar:
        if st.button("🇸🇦 العربية", use_container_width=True,
                     type="primary" if lang == "ar" else "secondary"):
            st.session_state.lang = "ar"
            st.rerun()
    with col_en:
        if st.button("🇬🇧 English", use_container_width=True,
                     type="primary" if lang == "en" else "secondary"):
            st.session_state.lang = "en"
            st.rerun()

    st.markdown("---")
    st.markdown(f"### Next-Step AI")

    page = st.radio(
        "Navigation",
        [
            t("nav_conversations", lang),
            t("nav_analysis", lang),
            t("nav_insights", lang),
            t("nav_maps", lang),
            t("nav_settings", lang),
        ],
        label_visibility="collapsed"
    )


# ══════════════════════════════════════════════════════════════
# PAGE 1 — CONVERSATIONS
# ══════════════════════════════════════════════════════════════
def conversations_page():
    st.title(t("page_conversations_title", lang))

    tab_paste, tab_upload = st.tabs([t("tab_paste", lang), t("tab_upload", lang)])

    with tab_paste:
        st.info(t("tip_paste", lang))
        label   = st.text_input(t("label_label", lang), placeholder=t("label_label_placeholder", lang), key="p_label")
        source  = st.selectbox(t("label_source", lang), ["Claude", "GPT", "Gemini", "Other"], key="p_src")
        content = st.text_area(t("label_content", lang), height=220, key="p_content")

        if st.button(t("btn_add", lang), type="primary", use_container_width=True, key="btn_paste_add"):
            if label and content:
                with st.spinner(t("spinner_compressing", lang)):
                    conv_id = memory.add_conversation(label, source, content)
                c = db.get_conversation(conv_id)
                orig = c.get("word_count", 1) or 1
                comp = c.get("compressed_word_count", orig) or orig
                reduction = max(0, (1 - comp / orig) * 100)
                st.success(t("success_added", lang))
                st.markdown(
                    f'<div class="comp-stat">'
                    f'{t("label_original", lang)}: {orig} {t("label_words", lang)} &nbsp;→&nbsp; '
                    f'{t("label_compressed", lang)}: {comp} {t("label_words", lang)} '
                    f'({reduction:.0f}% {t("label_compression", lang)})'
                    f'</div>',
                    unsafe_allow_html=True
                )
            else:
                st.error(t("err_fill_fields", lang))

    with tab_upload:
        f_label  = st.text_input(t("label_label", lang), placeholder=t("label_label_placeholder", lang), key="u_label")
        f_source = st.selectbox(t("label_source", lang), ["Claude", "GPT", "Gemini", "Other"], key="u_src")
        file     = st.file_uploader(t("tab_upload", lang), type=["txt", "md", "json"], key="u_file")

        if st.button(t("btn_upload_add", lang), type="primary", use_container_width=True, key="btn_upload_go"):
            if file and f_label:
                text = file.read().decode("utf-8")
                with st.spinner(t("spinner_compressing", lang)):
                    conv_id = memory.add_conversation(f_label, f_source, text)
                c = db.get_conversation(conv_id)
                orig = c.get("word_count", 1) or 1
                comp = c.get("compressed_word_count", orig) or orig
                reduction = max(0, (1 - comp / orig) * 100)
                st.success(t("success_uploaded", lang))
                st.markdown(
                    f'<div class="comp-stat">'
                    f'{t("label_original", lang)}: {orig} {t("label_words", lang)} &nbsp;→&nbsp; '
                    f'{t("label_compressed", lang)}: {comp} {t("label_words", lang)} '
                    f'({reduction:.0f}% {t("label_compression", lang)})'
                    f'</div>',
                    unsafe_allow_html=True
                )
            else:
                st.error(t("err_fill_file", lang))

    st.markdown("---")
    st.subheader(t("section_all_conversations", lang))

    convs = db.get_all_conversations()
    if not convs:
        st.info(t("no_conversations", lang))
        return

    # Header row
    cols = st.columns([3, 1.5, 1.5, 1.5, 2, 0.6])
    for col, label in zip(cols, [
        t("col_label", lang), t("col_source", lang),
        t("col_size", lang), t("col_compressed", lang),
        t("col_status", lang), ""
    ]):
        col.markdown(f"**{label}**")

    for c in convs:
        orig = c.get("word_count") or 0
        comp = c.get("compressed_word_count") or 0
        is_analyzed = c["status"] == "analyzed"
        badge = f'<span class="badge-analyzed">{t("status_analyzed", lang)}</span>' if is_analyzed \
                else f'<span class="badge-pending">{t("status_pending", lang)}</span>'

        cols = st.columns([3, 1.5, 1.5, 1.5, 2, 0.6])
        cols[0].write(f"**{c['label']}**")
        cols[1].write(c["source"])
        cols[2].write(f"{orig:,} {t('label_words', lang)}")
        cols[3].write(f"{comp:,} {t('label_words', lang)}")
        cols[4].markdown(badge, unsafe_allow_html=True)
        if cols[5].button("🗑️", key=f"del_{c['id']}"):
            db.delete_conversation(c["id"])
            st.rerun()


# ══════════════════════════════════════════════════════════════
# PAGE 2 — ANALYSIS
# ══════════════════════════════════════════════════════════════
def _render_research_discoveries(research_data: dict):
    """Render Research Agent discoveries in a collapsible section."""
    expander_label = t("research_discoveries_heading", lang)
    
    # If no research_data or no discoveries list, show fallback inside the expander
    if not research_data or not research_data.get("discoveries"):
        with st.expander(expander_label):
            if lang == "ar":
                st.info("لم يعثر وكيل البحث على اكتشافات خارجية في هذا التحليل")
            else:
                st.info("Research Agent found no external discoveries in this analysis")
        return

    discoveries = research_data.get("discoveries", [])
    research_summary = research_data.get("research_summary", "")

    with st.expander(expander_label):
        if research_summary:
            st.caption(research_summary)

        if not discoveries:
            if lang == "ar":
                st.info("لم يعثر وكيل البحث على اكتشافات خارجية في هذا التحليل")
            else:
                st.info("Research Agent found no external discoveries in this analysis")
            return

        for d in discoveries:
            title = d.get("title", "")
            dtype = d.get("type", "concept")
            relevance = d.get("relevance", "")
            suggested_angle = d.get("suggested_angle", "")
            source = d.get("source", "")

            with st.container(border=True):
                st.markdown(f"**{title}** `{dtype}`")
                if relevance:
                    st.markdown(f"- {relevance}")
                if suggested_angle:
                    st.markdown(f"- {suggested_angle}")
                if source:
                    st.caption(source)


def _render_ensemble(ensemble_data: dict):
    """Render Domain Specialist Analysis in a collapsible section."""
    if not ensemble_data:
        with st.expander(t("ensemble_heading", lang)):
            st.info(t("ensemble_not_run", lang))
        return

    completion = ensemble_data.get("completion_findings", [])
    alignment = ensemble_data.get("alignment_findings", [])
    contradiction = ensemble_data.get("contradiction_findings", [])

    if not any([completion, alignment, contradiction]):
        with st.expander(t("ensemble_heading", lang)):
            st.info(t("ensemble_not_run", lang))
        return

    with st.expander(t("ensemble_heading", lang)):
        if completion:
            st.markdown(f"**{t('ensemble_missing', lang)}:**")
            for f in completion:
                st.markdown(f"- {f}")

        if alignment:
            st.markdown(f"**{t('ensemble_adjacent', lang)}:**")
            for f in alignment:
                st.markdown(f"- {f}")

        if contradiction:
            st.markdown(f"**{t('ensemble_challenges', lang)}:**")
            for f in contradiction:
                st.markdown(f"- {f}")


def _render_latest_ensemble():
    """Render the ensemble for the most recent report (loaded from DB)."""
    conn = db.get_connection()
    latest = conn.execute("SELECT id FROM daily_reports ORDER BY timestamp DESC LIMIT 1").fetchone()
    conn.close()
    if latest:
        ensemble_data = db.get_ensemble_by_report(latest["id"])
        if ensemble_data:
            _render_ensemble(ensemble_data)


def analysis_page():
    st.title(t("page_analysis_title", lang))

    pending = memory.get_pending_conversations()
    n = len(pending)
    label_key = "pending_info" if n == 1 else "pending_info_plural"
    st.info(f"**{n}** {t(label_key, lang)}")

    if st.button(t("btn_analyze", lang), type="primary", use_container_width=True, disabled=(n == 0)):
        with st.spinner(t("spinner_analyzing", lang)):
            report, contextual_instructions, research_data, context_stats, calibration_results, report_id = asyncio.run(analyze_and_report(lang=lang))
        st.success(t("analysis_done", lang))
        st.markdown(report)

        # Show context stats
        if context_stats:
            included = context_stats.get("conversations_included", 0)
            truncated = context_stats.get("conversations_truncated", 0)
            ctx_line = t("context_included", lang).format(included=included)
            if truncated > 0:
                ctx_line += t("context_truncated", lang).format(truncated=truncated)
            st.caption(ctx_line)

        # Calibration note
        if calibration_results and calibration_results.get("insights_weakened", 0) > 0:
            n_cal = calibration_results["insights_weakened"]
            st.caption(t("calibration_note", lang).format(n=n_cal))

        # Show which maps influenced this analysis
        active_maps = db.get_all_active_maps()
        active_types = [mt for mt, inputs in active_maps.items() if any(inp.get("content") for inp in inputs)]
        if active_types:
            map_names = {
                "cognitive": t("map_cognitive", lang),
                "behavioral": t("map_behavioral", lang),
                "personal": t("map_personal", lang),
            }
            maps_str = ", ".join(map_names[mt] for mt in active_types)
        else:
            maps_str = t("maps_none", lang)
        st.caption(f"**{t('maps_used_label', lang)}:** {maps_str}")

        if contextual_instructions:
            st.markdown("---")
            st.subheader(t("contextual_instructions_heading", lang))
            st.caption(t("contextual_instructions_tip", lang))
            with st.container(border=True):
                st.code(contextual_instructions, language="markdown")

        # Research Agent Discoveries
        _render_research_discoveries(research_data)

        # Domain Specialist Analysis
        if report_id:
            ensemble_data = db.get_ensemble_by_report(report_id)
            _render_ensemble(ensemble_data)
        
        # Ready Prompts Usage Guide
        if "###" in report and (lang == "ar" or "Ready Prompts" in report):
            st.markdown("---")
            if lang == "ar":
                st.info("""**كيف تستخدم هذه المخرجات:**
١. الصق تعليمات السياق في بداية محادثة جديدة مع أي نموذج ذكاء اصطناعي
٢. اختر البرومبت الأهم لك والصقه في نفس المحادثة
٣. يمكنك استخدام عدة برومبتات في نفس المحادثة بالترتيب
٤. كل برومبت يفتح زاوية مختلفة — اختر حسب أولويتك""")
            else:
                st.info("""**How to use these outputs:**
1. Paste the Contextual Instructions at the start of a new conversation with any AI model
2. Choose the most relevant prompt and paste it next
3. You can use multiple prompts in the same conversation in order
4. Each prompt opens a different angle — choose by priority""")
    elif n == 0:
        st.warning(t("no_pending", lang))

    # Past reports in sidebar-style expander
    st.markdown("---")
    st.subheader(t("past_reports", lang))
    os.makedirs(REPORTS_DIR, exist_ok=True)
    reports = sorted(glob.glob(os.path.join(REPORTS_DIR, "*.md")), reverse=True)

    if not reports:
        st.caption(t("no_reports", lang))
    else:
        names = [os.path.basename(r) for r in reports]
        sel = st.selectbox(t("select_report", lang), names, key="sel_report")
        if sel:
            path = os.path.join(REPORTS_DIR, sel)
            with open(path, "r", encoding="utf-8") as f:
                report_text = f.read()
                st.markdown(report_text)

            date_prefix = sel.replace("report_", "").replace(".md", "")
            conn = db.get_connection()
            dr_row = conn.execute("SELECT id FROM daily_reports WHERE date = ?", (date_prefix,)).fetchone()
            conn.close()

            if dr_row:
                report_id = dr_row["id"]
                
                # Contextual Instructions
                ci_data = db.get_instruction_by_report(report_id)
                if ci_data:
                    st.markdown("---")
                    st.subheader(t("contextual_instructions_heading", lang))
                    st.caption(t("contextual_instructions_tip", lang))
                    with st.container(border=True):
                        st.code(ci_data["content"], language="markdown")

                # Research
                research_data = db.get_research_by_report(report_id)
                _render_research_discoveries(research_data)

                # Domain Ensemble
                ensemble_data = db.get_ensemble_by_report(report_id)
                _render_ensemble(ensemble_data)

                # Usage Guide
                if "###" in report_text and (lang == "ar" or "Ready Prompts" in report_text):
                    st.markdown("---")
                    if lang == "ar":
                        st.info("""**كيف تستخدم هذه المخرجات:**
١. الصق تعليمات السياق في بداية محادثة جديدة مع أي نموذج ذكاء اصطناعي
٢. اختر البرومبت الأهم لك والصقه في نفس المحادثة
٣. يمكنك استخدام عدة برومبتات في نفس المحادثة بالترتيب
٤. كل برومبت يفتح زاوية مختلفة — اختر حسب أولويتك""")
                    else:
                        st.info("""**How to use these outputs:**
1. Paste the Contextual Instructions at the start of a new conversation with any AI model
2. Choose the most relevant prompt and paste it next
3. You can use multiple prompts in the same conversation in order
4. Each prompt opens a different angle — choose by priority""")


# ══════════════════════════════════════════════════════════════
# PAGE 3 — INSIGHTS
# ══════════════════════════════════════════════════════════════
def insights_page():
    st.title(t("page_insights_title", lang))

    insights = db.get_all_insights()
    if not insights:
        st.info(t("no_insights", lang))
        return

    type_labels = {
        "informational": t("type_informational", lang),
        "inferential":   t("type_inferential", lang),
        "complementary": t("type_complementary", lang),
        "pattern":       t("type_pattern", lang),
    }

    filter_options = (
        [t("filter_all", lang)]
        + list(type_labels.values())
        + ["──"]
        + [t("filter_flagged", lang), t("filter_pending", lang)]
    )
    chosen = st.selectbox(t("filter_type", lang), filter_options, key="insights_filter")

    # Reverse map for filtering
    reverse_map = {v: k for k, v in type_labels.items()}
    if chosen == t("filter_flagged", lang):
        insights = [i for i in insights if i.get("calibration_status") == "flagged"]
    elif chosen == t("filter_pending", lang):
        insights = [i for i in insights if i.get("calibration_status") == "pending_confirmation"]
    elif chosen != t("filter_all", lang) and chosen != "──":
        raw_type = reverse_map.get(chosen, chosen)
        insights = [i for i in insights if i["insight_type"] == raw_type]

    st.metric(t("total_insights", lang), len(insights))
    st.markdown("---")

    for i in insights:
        itype = i["insight_type"]
        chip_label = type_labels.get(itype, itype)
        impact = i.get("impact", "medium")

        header = f'<span class="chip-{itype}">{chip_label}</span> &nbsp; <span class="chip-{impact}">{impact.upper()}</span>'

        with st.expander(f"{i['content'][:80]}...", expanded=False):
            st.markdown(header, unsafe_allow_html=True)

            # Calibration badge
            cal_status = i.get("calibration_status") or "active"
            if cal_status == "flagged":
                st.markdown(f'<span class="badge-flagged">{t("flagged_badge", lang)}</span>', unsafe_allow_html=True)
            elif cal_status == "pending_confirmation":
                st.markdown(f'<span class="badge-pending">{t("pending_badge", lang)}</span>', unsafe_allow_html=True)
            elif cal_status == "weakened":
                st.markdown(f'<span class="badge-weakened">{t("weakened_badge", lang)}</span>', unsafe_allow_html=True)

            st.markdown(f"**{t('label_content_insight', lang)}:** {i['content']}")
            
            if i.get("why_it_matters"):
                st.markdown(f"**{t('label_why_it_matters', lang)}:** {i['why_it_matters']}")
            
            if i.get("ready_prompt"):
                st.markdown(f"**{t('label_ready_prompt', lang)}:**")
                st.info(i['ready_prompt'])
            
            if i.get("confidence"):
                reason = f" ({i['confidence_reason']})" if i.get("confidence_reason") else ""
                st.markdown(f"**{t('label_confidence', lang)}:** {i['confidence']}{reason}")
                
            if i.get("evidence"):
                st.markdown(f"**{t('label_evidence', lang)}:** {i['evidence']}")
            if i.get("conversations_referenced"):
                import json
                try:
                    refs = json.loads(i["conversations_referenced"])
                    refs_str = "، ".join(refs) if lang == "ar" else ", ".join(refs)
                except Exception:
                    refs_str = str(i["conversations_referenced"])
                st.caption(f"{t('label_refs', lang)}: {refs_str}")
            st.caption(f"{t('label_date', lang)}: {i['timestamp'][:10]}")

            current_score = i.get("quality_score") or 3
            score = st.slider(
                t("label_quality", lang), 1, 5, current_score,
                key=f"slider_{i['id']}"
            )
            if st.button(t("btn_save_rating", lang), key=f"rate_{i['id']}"):
                db.rate_insight(i["id"], score)
                st.success(t("rating_saved", lang))


# ══════════════════════════════════════════════════════════════
# PAGE 4 — MAPS
# ══════════════════════════════════════════════════════════════
def _map_status_indicator(map_inputs: list, total_fields: int):
    """Return status label for a map section."""
    filled = sum(1 for m in map_inputs if m.get("content"))
    if filled == 0:
        return t("maps_status_empty", lang), "#6b7280"
    elif filled >= total_fields:
        return t("maps_status_complete", lang), "#22c55e"
    else:
        return t("maps_status_partial", lang), "#f59e0b"


def _get_saved_value(map_inputs: list, input_type: str) -> str:
    for m in map_inputs:
        if m["input_type"] == input_type:
            return m.get("content", "") or ""
    return ""


def _get_last_updated(map_inputs: list) -> str:
    if not map_inputs:
        return ""
    dates = [m.get("last_updated", "") for m in map_inputs if m.get("last_updated")]
    if dates:
        return max(dates)[:10]
    return ""


BEHAVIORAL_PROMPT = """I want you to analyze our conversation history together and give me a behavioral profile based on what you've observed. Focus on:
1. How I make decisions — fast or deliberate, with full picture or incrementally
2. What types of tasks I start but don't finish
3. How I respond under pressure or uncertainty
4. My recurring work patterns — what I repeat
5. The difference between topics where I go deep vs shallow

Be direct. No flattery. Give me specific observations with examples from our conversations.
Format: one paragraph per point."""

COMMUNICATION_PROMPT = """Based on our conversations, give me an honest analysis of my communication and thinking style. Cover:
1. How I structure arguments — from framework to details or from details to framework
2. My communication style — direct or cushioned, formal or informal
3. How I respond to challenge or disagreement
4. My core values as they appear in how I discuss things
5. What makes me most effective in conversation

Be specific. Use examples from our conversations.
No generic personality descriptions.
Format: one paragraph per point."""


def maps_page():
    st.title(t("page_maps_title", lang))

    all_maps = db.get_all_active_maps()

    # ── Status indicators ──
    st.subheader(t("maps_status_heading", lang))
    col1, col2, col3 = st.columns(3)
    for col, map_key, map_name, field_count in [
        (col1, "cognitive", t("map_cognitive", lang), 2),
        (col2, "behavioral", t("map_behavioral", lang), 3),
        (col3, "personal", t("map_personal", lang), 2),
    ]:
        inputs = all_maps.get(map_key, [])
        status, color = _map_status_indicator(inputs, field_count)
        col.markdown(
            f'<div style="padding:10px;border-radius:8px;background:#1a1d27;'
            f'border-left:3px solid {color};">'
            f'<div style="font-weight:600;">{map_name}</div>'
            f'<div style="color:{color};font-size:13px;">{status}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    st.markdown("---")

    # Pre-load saved values
    cog_inputs = all_maps.get("cognitive", [])
    beh_inputs = all_maps.get("behavioral", [])
    per_inputs = all_maps.get("personal", [])

    # ── COGNITIVE MAP ──
    with st.expander(f"🧠 {t('map_cognitive', lang)} — {t('map_cognitive_desc', lang)}", expanded=True):
        last_upd = _get_last_updated(cog_inputs)
        if last_upd:
            st.caption(t("maps_last_updated", lang).format(last_upd))

        external_links = st.text_area(
            t("maps_external_links", lang),
            value=_get_saved_value(cog_inputs, "external_links"),
            help=t("maps_external_links_help", lang),
            height=68, key="map_ext_links"
        )
        knowledge_summary = st.text_area(
            t("maps_knowledge_summary", lang),
            value=_get_saved_value(cog_inputs, "knowledge_summary"),
            help=t("maps_knowledge_summary_help", lang),
            height=120, key="map_know_sum"
        )

    # ── BEHAVIORAL MAP ──
    with st.expander(f"⚡ {t('map_behavioral', lang)} — {t('map_behavioral_desc', lang)}", expanded=False):
        last_upd = _get_last_updated(beh_inputs)
        if last_upd:
            st.caption(t("maps_last_updated", lang).format(last_upd))

        st.markdown(f"**{t('maps_inspire_qa', lang)}**")
        inspire_answers = {}
        for qi, qkey in enumerate(["maps_q1", "maps_q2", "maps_q3", "maps_q4", "maps_q5"], 1):
            inspire_answers[qi] = st.text_area(
                t(qkey, lang),
                value=_get_saved_value(beh_inputs, f"inspire_q{qi}"),
                height=68, key=f"map_inspire_{qi}"
            )

        ai_behavioral = st.text_area(
            t("maps_ai_behavioral", lang),
            value=_get_saved_value(beh_inputs, "ai_behavioral"),
            help=t("maps_ai_behavioral_help", lang),
            height=120, key="map_ai_beh"
        )

        with st.expander(t("maps_get_behavioral_prompt", lang)):
            st.code(BEHAVIORAL_PROMPT, language="text")

    # ── PERSONAL MAP ──
    with st.expander(f"🎯 {t('map_personal', lang)} — {t('map_personal_desc', lang)}", expanded=False):
        last_upd = _get_last_updated(per_inputs)
        if last_upd:
            st.caption(t("maps_last_updated", lang).format(last_upd))

        personality = st.text_area(
            t("maps_personality_result", lang),
            value=_get_saved_value(per_inputs, "personality"),
            help=t("maps_personality_help", lang),
            height=120, key="map_personality"
        )
        comm_style = st.text_area(
            t("maps_comm_style", lang),
            value=_get_saved_value(per_inputs, "comm_style"),
            help=t("maps_comm_style_help", lang),
            height=120, key="map_comm_style"
        )

        with st.expander(t("maps_get_comm_prompt", lang)):
            st.code(COMMUNICATION_PROMPT, language="text")

    # ── SAVE ──
    st.markdown("---")
    if st.button(t("btn_save_maps", lang), type="primary", use_container_width=True):
        saved_count = 0
        # Cognitive
        if external_links.strip():
            db.upsert_map_input("cognitive", "external_links", external_links.strip())
            saved_count += 1
        if knowledge_summary.strip():
            db.upsert_map_input("cognitive", "knowledge_summary", knowledge_summary.strip())
            saved_count += 1
        # Behavioral
        for qi in range(1, 6):
            val = inspire_answers[qi].strip()
            if val:
                db.upsert_map_input("behavioral", f"inspire_q{qi}", val)
                saved_count += 1
        if ai_behavioral.strip():
            db.upsert_map_input("behavioral", "ai_behavioral", ai_behavioral.strip())
            saved_count += 1
        # Personal
        if personality.strip():
            db.upsert_map_input("personal", "personality", personality.strip())
            saved_count += 1
        if comm_style.strip():
            db.upsert_map_input("personal", "comm_style", comm_style.strip())
            saved_count += 1

        if saved_count > 0:
            st.success(t("maps_saved", lang))
        else:
            st.warning(t("maps_status_empty", lang))
        st.rerun()


# ══════════════════════════════════════════════════════════════
# PAGE 5 — SETTINGS
# ══════════════════════════════════════════════════════════════
def settings_page():
    st.title(t("page_settings_title", lang))

    st.info(t("settings_api_info", lang))
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    st.code(env_path, language="text")

    st.markdown("---")
    st.subheader(t("settings_model_section", lang))
    st.markdown(f"- **{t('settings_insight_model', lang)}:** `{INSIGHT_MODEL}`")
    st.markdown(f"- **{t('settings_synthesis_model', lang)}:** `{SYNTHESIS_MODEL}`")
    st.markdown(f"- **{t('settings_compressor_model', lang)}:** `{COMPRESSOR_MODEL}`")

    st.markdown("---")
    with st.expander(f"⚠️ {t('btn_clear', lang)}", expanded=False):
        st.warning(t("clear_confirm", lang))
        if st.button(t("btn_clear", lang), type="primary"):
            # 1. Clear all DB tables
            conn = db.get_connection()
            for tbl in ["conversations", "canonical_units", "insights", "daily_reports", "contextual_instructions", "research_results", "user_maps", "domain_ensemble_results", "calibration_log"]:
                conn.execute(f"DELETE FROM {tbl}")
            conn.commit()
            conn.close()
            # 2. Delete all report files from disk
            import glob as _glob
            report_files = _glob.glob(os.path.join(REPORTS_DIR, "*.md"))
            for f in report_files:
                os.remove(f)
            st.success(t("cleared", lang))
            st.rerun()


# ══════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════
if page == t("nav_conversations", lang):
    conversations_page()
elif page == t("nav_analysis", lang):
    analysis_page()
elif page == t("nav_insights", lang):
    insights_page()
elif page == t("nav_maps", lang):
    maps_page()
elif page == t("nav_settings", lang):
    settings_page()
