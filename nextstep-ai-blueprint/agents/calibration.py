import json
from openai import OpenAI
from config import OPENAI_API_KEY, CALIBRATION_MODEL


CALIBRATION_SYSTEM_PROMPT = """You are the Calibration Agent for Next-Step AI.

Your job: audit existing insights against new evidence and \
identify those that should be weakened, flagged, or confirmed.

WEAKENING RULES — weaken an insight if:
- New findings directly contradict it with stronger evidence
- It was marked tentative and has not been reinforced \
across 3+ analyses
- Its evidence is now known to be from a single conversation \
and newer conversations show different patterns
- The user's maps context contradicts its core claim

FLAGGING RULES — flag (not weaken) if:
- The insight may still be valid but context has shifted
- Confidence was moderate and no reinforcing evidence exists
- The insight is older than 30 days with no user interaction

CONFIRMATION REQUEST — request user confirmation if:
- A HIGH impact insight is being considered for weakening
- The evidence is ambiguous — could support or contradict

HARD LIMITS — never:
- Weaken insights with quality_score >= 4 (user rated them good)
- Silently remove any insight
- Alter the content of any insight
- Weaken more than 30% of reviewed insights in one run \
(if this threshold is exceeded, flag instead of weaken)

Return ONLY valid JSON matching the output structure."""


def _build_findings_block(new_findings: list) -> str:
    lines = []
    for f in new_findings:
        category = f.get("type", "unknown")
        impact = f.get("impact", "medium")
        missing_angle = f.get("missing_angle", "")[:100]
        evidence = f.get("evidence", "")[:100]
        lines.append(f"- [{category}] [{impact}]: {missing_angle} | {evidence}")
    return "\n".join(lines) if lines else "- No new findings"


def _build_insights_block(existing_insights: list) -> str:
    lines = []
    for i in existing_insights:
        iid = i.get("id", "?")[:8]
        itype = i.get("insight_type", "?")
        confidence = i.get("confidence", "?")
        impact = i.get("impact", "?")
        quality_score = i.get("quality_score") or 0
        missing_angle = (i.get("missing_angle") or i.get("content", ""))[:100]
        evidence = (i.get("evidence") or "")[:100]
        lines.append(
            f"- [{iid}] [{itype}] [{confidence}] [{impact}] "
            f"(score:{quality_score}): {missing_angle} | {evidence}"
        )
    return "\n".join(lines) if lines else "- No existing insights"


def _parse_response(text: str, insights_reviewed: int) -> dict:
    """Parse the JSON response from the API, with cleanup."""
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        data = json.loads(text.strip())
    except (json.JSONDecodeError, IndexError):
        return {
            "weakened": [],
            "stale_map_inputs": [],
            "calibration_summary": "Calibration parse error",
            "insights_reviewed": insights_reviewed,
            "insights_weakened": 0,
        }

    # Enforce 30% cap: if too many weakened, convert to flags
    weakened = data.get("weakened", [])
    cap = max(1, int(insights_reviewed * 0.3))
    if len(weakened) > cap:
        for w in weakened[cap:]:
            if w.get("action") == "weaken":
                w["action"] = "flag"

    return {
        "weakened": data.get("weakened", []),
        "stale_map_inputs": data.get("stale_map_inputs", []),
        "calibration_summary": data.get("calibration_summary", ""),
        "insights_reviewed": insights_reviewed,
        "insights_weakened": len(data.get("weakened", [])),
    }


FALLBACK_RESULT = {
    "weakened": [],
    "stale_map_inputs": [],
    "calibration_summary": "Calibration unavailable",
    "insights_reviewed": 0,
    "insights_weakened": 0,
}


def run_calibration(
    new_findings: list,
    existing_insights: list,
    maps_context: str,
    lang: str,
) -> dict:
    """Audit existing insights against new evidence."""
    if not existing_insights:
        return {
            "weakened": [],
            "stale_map_inputs": [],
            "calibration_summary": "No existing insights to review",
            "insights_reviewed": 0,
            "insights_weakened": 0,
        }

    if not OPENAI_API_KEY or "-key-" in OPENAI_API_KEY:
        return FALLBACK_RESULT

    new_findings_block = _build_findings_block(new_findings)
    existing_insights_block = _build_insights_block(existing_insights)

    user_prompt = f"""New findings from current analysis:
{new_findings_block}

Existing insights to review:
{existing_insights_block}

Current maps context:
{maps_context or 'No maps context available'}

Audit the existing insights against the new evidence.
Apply the weakening, flagging, and confirmation rules.
Return JSON only."""

    client = OpenAI(api_key=OPENAI_API_KEY)

    try:
        res = client.chat.completions.create(
            model=CALIBRATION_MODEL,
            messages=[
                {"role": "system", "content": CALIBRATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            max_completion_tokens=2000,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return _parse_response(res.choices[0].message.content, len(existing_insights))
    except Exception:
        return FALLBACK_RESULT
