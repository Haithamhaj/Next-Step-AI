import os
import json
from openai import OpenAI
from config import OPENAI_API_KEY, SYNTHESIS_MODEL, CONTEXTUAL_INSTRUCTIONS_MODEL, PROMPTS_DIR

def load_prompt(filename: str) -> str:
    path = os.path.join(PROMPTS_DIR, filename)
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def generate_report(analysis_data: dict, date_str: str, lang: str = "ar") -> str:
    system_prompt_raw = load_prompt("synthesis_system.txt")
    system_prompt = system_prompt_raw.replace("{lang}", lang) if system_prompt_raw else "Format this data as a clean markdown report."

    # Separate findings by category for the synthesis model
    type_to_cat = {
        "informational": "completion",
        "complementary": "alignment",
        "inferential": "contradiction",
        "completion": "completion",
        "alignment": "alignment",
        "contradiction": "contradiction"
    }
    by_category = {"completion": [], "alignment": [], "contradiction": []}
    for i in analysis_data.get('findings', []):
        raw_cat = i.get('category') or i.get('type', '')
        cat = type_to_cat.get(raw_cat.lower(), 'completion')
        by_category[cat].append(i)

    insights_text = f"Summary: {analysis_data.get('session_summary', '')}\n\n"

    cat_labels = {
        "contradiction": ("CONTRADICTION — Risks & Challenges", "missing_angle", "why_it_matters"),
        "completion": ("COMPLETION — What's Missing", "missing_angle", "why_it_matters"),
        "alignment": ("ALIGNMENT — Adjacent Angles", "missing_angle", "why_it_matters"),
    }

    # Only include categories that have findings
    for cat_key, (cat_header, field1, field2) in cat_labels.items():
        cat_findings = by_category[cat_key]
        if cat_findings:
            insights_text += f"=== {cat_header} ===\n"
            for idx, i in enumerate(cat_findings):
                insights_text += f"  Finding {idx+1}:\n"
                insights_text += f"  - Type: {i.get('type')}\n"
                insights_text += f"  - Category: {cat_key}\n"
                insights_text += f"  - Confidence: {i.get('confidence')} ({i.get('confidence_reason')})\n"
                insights_text += f"  - Impact: {i.get('impact')}\n"
                insights_text += f"  - Missing Angle: {i.get('missing_angle')}\n"
                insights_text += f"  - Why It Matters: {i.get('why_it_matters')}\n"
                insights_text += f"  - Ready Prompt: {i.get('ready_prompt')}\n"
                insights_text += f"  - Evidence: {i.get('evidence')}\n"
                insights_text += f"  - Profile Connection: {i.get('profile_connection')}\n"
                insights_text += f"  - Conversations Referenced: {i.get('conversations_referenced')}\n\n"
        
    if not analysis_data.get('has_insight') or not any(by_category.values()):
        return "لا توجد نتائج مهمة للتحليل — No significant findings."
        
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        if not OPENAI_API_KEY or "-key-" in OPENAI_API_KEY:
            raise ValueError("No valid API key")
            
        res = client.chat.completions.create(
            model=SYNTHESIS_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Date: {date_str}\n\nAnalysis Data:\n{insights_text}"}
            ],
            temperature=0.5,
            max_completion_tokens=2000
        )
        return res.choices[0].message.content
    except Exception as e:
        fallback = f"# Analysis Fallback ({date_str})\n\n"
        fallback += insights_text
        return fallback


FALLBACK_CONTEXTUAL_INSTRUCTIONS = (
    "You are an expert in the topic I am about to discuss. "
    "Give me specific, structured answers. No generic advice. "
    "If you are uncertain, say so explicitly."
)


def generate_contextual_instructions(
    analysis_data: dict,
    profile: str,
    lang: str,
    topic_summary: str
) -> str:
    system_prompt = f"""You are the Contextual Instructions Generator for Next-Step AI.

Your job: produce a short, paste-ready setup block the user
can place at the start of a new AI conversation before using
their Ready Prompts.

The Contextual Instructions MUST contain all 6 elements, built strictly from the actual findings provided:

1. ROLE: Define a specific expert role derived from the DOMINANT category of findings:
   - Most are CONTRADICTION -> Act as a critical reviewer and devil's advocate who challenges assumptions.
   - Most are COMPLETION -> Act as a domain specialist who identifies and fills structural gaps.
   - Most are ALIGNMENT -> Act as a practical expert in adjacent tools and system integration.
   Include 2-3 specific domain qualifications mentioned in the findings.
2. GOAL: One clear sentence stating what this session aims to achieve, derived from the top finding's 'why_it_matters'.
3. CONTEXT: 2-3 bullet points with specifics from the actual findings (facts, tools, or gaps discovered). Never a summary of the topic.
4. CONSTRAINTS: 3+ rules including:
   - "Do not provide generic or surface-level advice."
   - A constraint derived from the top CONTRADICTION finding (if any): e.g., "Do not validate [X] without challenging [Y] first."
5. OUTPUT FORMAT: Specify the structure every answer must follow, derived from finding categories:
   - If CONTRADICTION exists: "Structure every answer: Risk | Evidence | Mitigation"
   - If COMPLETION exists: "Structure every answer: Gap | Why it matters | How to close it"
   - If ALIGNMENT exists: "Structure every answer: Tool/Domain | Connection | First Step"
6. TONE: Direct, concise, expert-level. No flattery. Challenge assumptions.

Format: A single paste-ready block. No intro/outro text.
Length: 100-150 words maximum.
Language: {lang}."""

    findings = analysis_data.get("findings", [])
    findings_summary = ""
    categories = {"completion": 0, "alignment": 0, "contradiction": 0}
    type_to_cat = {"informational": "completion", "complementary": "alignment", "inferential": "contradiction"}
    
    for idx, f in enumerate(findings):
        cat = f.get("category") or type_to_cat.get(f.get("type", ""), "completion")
        categories[cat.lower()] = categories.get(cat.lower(), 0) + 1
        
        ma = (f.get("missing_angle") or "")[:300]
        wm = (f.get("why_it_matters") or "")[:300]
        if ma or wm:
            findings_summary += f"- [{cat.upper()}] {ma} (Why it matters: {wm})\n"

    if not findings_summary:
        findings_summary = "No specific findings available."

    profile_summary = (profile or "")[:500]

    user_prompt = f"""Findings from analysis (USE THESE TO BUILD THE INSTRUCTIONS):
{findings_summary}

Dominant Category Counts: {categories}

User profile context:
{profile_summary}

Topic summary (for context only): {topic_summary}

Generate the paste-ready Contextual Instructions block."""

    client = OpenAI(api_key=OPENAI_API_KEY)

    try:
        if not OPENAI_API_KEY or "-key-" in OPENAI_API_KEY:
            raise ValueError("No valid API key")

        res = client.chat.completions.create(
            model=CONTEXTUAL_INSTRUCTIONS_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_completion_tokens=1500
        )
        return res.choices[0].message.content
    except Exception:
        return FALLBACK_CONTEXTUAL_INSTRUCTIONS
