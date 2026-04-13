import os
from openai import OpenAI
from config import OPENAI_API_KEY, SYNTHESIS_MODEL, PROMPTS_DIR

def load_prompt(filename: str) -> str:
    path = os.path.join(PROMPTS_DIR, filename)
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def generate_report(analysis_data: dict, date_str: str, lang: str = "ar") -> str:
    system_prompt_raw = load_prompt("synthesis_system.txt")
    system_prompt = system_prompt_raw.replace("{lang}", lang) if system_prompt_raw else "Format this data as a clean markdown report."

    insights_text = f"Summary: {analysis_data.get('session_summary', '')}\n\n"
    for idx, i in enumerate(analysis_data.get('findings', [])):
        insights_text += f"Finding {idx+1}:\n"
        insights_text += f"- Type: {i.get('type')}\n"
        insights_text += f"- Confidence: {i.get('confidence')} ({i.get('confidence_reason')})\n"
        insights_text += f"- Impact: {i.get('impact')}\n"
        insights_text += f"- Missing Angle: {i.get('missing_angle')}\n"
        insights_text += f"- Why It Matters: {i.get('why_it_matters')}\n"
        insights_text += f"- Ready Prompt: {i.get('ready_prompt')}\n"
        insights_text += f"- Evidence: {i.get('evidence')}\n"
        insights_text += f"- Profile Connection: {i.get('profile_connection')}\n"
        insights_text += f"- Conversations Referenced: {i.get('conversations_referenced')}\n\n"
        
    if not analysis_data.get('has_insight') or not analysis_data.get('findings'):
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
            max_tokens=2000
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
    classified_findings: dict,
    profile: str,
    lang: str,
    topic_summary: str
) -> str:
    system_prompt = f"""You are the Contextual Instructions Generator for Next-Step AI.

Your job: produce a short, paste-ready setup block the user
can place at the start of a new AI conversation before using
their Ready Prompts.

The Contextual Instructions must:
1. Define the role the AI should take for this topic
2. Set 3-5 behavioral rules that prevent surface-level answers
3. Specify the output format the AI should follow
4. Include one anti-drift rule: what the AI should NOT do

Format:
A single paste-ready block — not a list of instructions about
how to write instructions. The user pastes this directly.

Length: 100-150 words maximum. Concise and direct.

Rules:
- Make it specific to the topic discussed — not generic
- Base the role on what the topic actually needs
- Base the behavioral rules on what was missing in the analysis
- Do not reference Next-Step AI or the analysis process
- Write in the user's selected language: {lang}
- Do not praise the user
- Do not add explanatory text outside the paste-ready block"""

    findings = classified_findings.get("findings", [])
    findings_summary = ""
    for idx, f in enumerate(findings):
        ma = (f.get("missing_angle") or "")[:300]
        wm = (f.get("why_it_matters") or "")[:300]
        if ma or wm:
            findings_summary += f"{idx+1}. {ma}"
            if wm:
                findings_summary += f" — {wm}"
            findings_summary += "\n"

    if not findings_summary:
        findings_summary = "No specific findings available."

    profile_summary = (profile or "")[:500]

    user_prompt = f"""Topic summary: {topic_summary}

Key findings from analysis:
{findings_summary}

User profile context:
{profile_summary}

Generate the Contextual Instructions block."""

    client = OpenAI(api_key=OPENAI_API_KEY)

    try:
        if not OPENAI_API_KEY or "-key-" in OPENAI_API_KEY:
            raise ValueError("No valid API key")

        res = client.chat.completions.create(
            model=SYNTHESIS_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        return res.choices[0].message.content
    except Exception:
        return FALLBACK_CONTEXTUAL_INSTRUCTIONS
