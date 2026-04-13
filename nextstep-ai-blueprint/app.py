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
    if not research_data:
        return

    discoveries = research_data.get("discoveries", [])
    research_summary = research_data.get("research_summary", "")

    expander_label = t("research_discoveries_heading", lang)
    with st.expander(expander_label):
        if research_summary:
            st.caption(research_summary)

        if not discoveries:
            st.info(t("no_discoveries", lang))
            return

        import json
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


def analysis_page():
    st.title(t("page_analysis_title", lang))

    pending = memory.get_pending_conversations()
    n = len(pending)
    label_key = "pending_info" if n == 1 else "pending_info_plural"
    st.info(f"**{n}** {t(label_key, lang)}")

    if st.button(t("btn_analyze", lang), type="primary", use_container_width=True, disabled=(n == 0)):
        with st.spinner(t("spinner_analyzing", lang)):
            report, contextual_instructions, research_data = asyncio.run(analyze_and_report(lang=lang))
        st.success(t("analysis_done", lang))
        st.markdown(report)

        if contextual_instructions:
            st.markdown("---")
            st.subheader(t("contextual_instructions_heading", lang))
            st.caption(t("contextual_instructions_tip", lang))
            with st.container(border=True):
                st.code(contextual_instructions, language="markdown")

        # Research Agent Discoveries
        _render_research_discoveries(research_data)
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
                st.markdown(f.read())

            # Load paired contextual instructions and research by matching on date prefix
            date_prefix = sel.replace("report_", "").replace(".md", "")
            conn = db.get_connection()
            ci_row = conn.execute(
                "SELECT ci.content FROM contextual_instructions ci "
                "JOIN daily_reports dr ON ci.report_id = dr.id "
                "WHERE dr.date = ?",
                (date_prefix,)
            ).fetchone()

            rr_row = conn.execute(
                "SELECT rr.discoveries, rr.research_summary FROM research_results rr "
                "JOIN daily_reports dr ON rr.report_id = dr.id "
                "WHERE dr.date = ?",
                (date_prefix,)
            ).fetchone()
            conn.close()

            if ci_row:
                st.markdown("---")
                st.subheader(t("contextual_instructions_heading", lang))
                st.caption(t("contextual_instructions_tip", lang))
                with st.container(border=True):
                    st.code(ci_row["content"], language="markdown")

            if rr_row:
                import json
                try:
                    past_discoveries = json.loads(rr_row["discoveries"]) if rr_row["discoveries"] else []
                except Exception:
                    past_discoveries = []
                past_research = {
                    "discoveries": past_discoveries,
                    "research_summary": rr_row["research_summary"] or ""
                }
                _render_research_discoveries(past_research)


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

    filter_options = [t("filter_all", lang)] + list(type_labels.values())
    chosen = st.selectbox(t("filter_type", lang), filter_options, key="insights_filter")

    # Reverse map for filtering
    reverse_map = {v: k for k, v in type_labels.items()}
    if chosen != t("filter_all", lang):
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
# PAGE 4 — SETTINGS
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
            for tbl in ["conversations", "canonical_units", "insights", "daily_reports", "contextual_instructions", "research_results"]:
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
elif page == t("nav_settings", lang):
    settings_page()
