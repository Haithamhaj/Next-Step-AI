import os
import json
from openai import OpenAI
from config import OPENAI_API_KEY, PROMPT_ARCHITECT_MODEL, PROMPTS_DIR


SYSTEM_PROMPT = """You are the Prompt Architect for Next-Step AI.

Your only job: build complete, paste-ready prompts for each
finding. You receive findings that already have analysis —
missing_angle, why_it_matters, category, evidence.
Your job is to turn each finding into a prompt the user
can paste directly into any AI model to close that gap.

STRUCTURE — every prompt MUST contain all 5 elements:
1. ROLE: "Act as a [specific role]"
   - COMPLETION finding -> domain expert who fills gaps
   - ALIGNMENT finding -> practitioner who uses the adjacent tool/domain in real work
   - CONTRADICTION finding -> critical reviewer who challenges assumptions
2. GOAL: One clear sentence stating exactly what to accomplish, derived from why_it_matters.
3. CONTEXT: 2-3 bullet points with specifics from the conversation. Minimum 1 direct reference to what was discussed. Never generic.
4. CONSTRAINTS: Minimum 2 rules:
   - No generic advice.
   - No repeating what was already in the conversation.
   - Category-specific:
     - COMPLETION -> "Do not explain what I already know, focus only on what is missing"
     - ALIGNMENT -> "Do not describe the tool generally, show specifically how it connects to my case"
     - CONTRADICTION -> "Do not soften the problem, state it directly with consequences"
5. OUTPUT FORMAT: Request a specific structure (numbered points, table, step-by-step, etc.). Never free prose.

FAILURE TEST — reject any prompt that:
- Could be written without reading the conversation
- Uses the word "general" or "overview"
- Has no specific structure requirement
- Is shorter than 80 words or longer than 150 words.

Language: write ALL prompts in {lang}.
Return JSON only in the format:
{
  "completion": [{"missing_angle": "...", "ready_prompt": "..."}],
  "alignment": [...],
  "contradiction": [...]
}"""


USER_PROMPT_TEMPLATE = """Conversations (for context — do not summarize, use for specifics):
{conversations_excerpt}

User maps context:
{maps_context}

Findings to build prompts for:

COMPLETION findings:
{completion_findings}

ALIGNMENT findings:
{alignment_findings}

CONTRADICTION findings:
{contradiction_findings}

For each finding, build a ready_prompt (80-150 words) that closes the specific gap.
Return the complete structure as JSON with all original findings plus the new ready_prompt fields.
Return JSON only."""


def _strip_ready_prompt(finding: dict) -> dict:
    """Remove ready_prompt from a finding before sending to the model."""
    cleaned = dict(finding)
    cleaned.pop("ready_prompt", None)
    return cleaned


def _build_fallback_prompt(finding: dict, category: str = "completion", lang: str = "ar") -> str:
    """Generate a structured 5-element prompt when the API call fails."""
    missing = finding.get("missing_angle", "this topic")
    why = finding.get("why_it_matters", "improving the overall quality of results")
    evidence = finding.get("evidence", "")

    # Clean excerpt: avoid mid-sentence truncation
    if evidence:
        excerpt = evidence[:200]
        # Try to find last sentence break
        for sep in (". ", ".\n", "؟ ", "? ", "! ", "। "):
            if sep in excerpt:
                excerpt = excerpt[:excerpt.rfind(sep) + 1]
                break
    else:
        excerpt = "the context discussed in the previous conversation"

    # 1. ROLE and 4. CONSTRAINTS (Category-specific)
    if category == "completion":
        role = "domain expert who specializes in identifying and filling strategic gaps"
        goal_prefix = "fill the critical missing gap regarding"
        constraint = "Do not explain what I already know, focus only on what is missing from the current approach."
        if lang == "ar":
            role = "خبير متخصص في تحديد سد الفجوات الاستراتيجية والمعرفية"
            goal_prefix = "سد الفجوة المعرفية الحرجة المتعلقة بـ"
            constraint = "لا تشرح ما أعرفه بالفعل، ركز حصرياً على ما هو مفقود في النهج الحالي."
    elif category == "alignment":
        role = "practitioner who uses specialized tools and neighboring domains in real-world environments"
        goal_prefix = "explain the adjacent tool or domain of"
        constraint = "Do not describe the tool generally, show specifically how it connects to my case and provides value."
        if lang == "ar":
            role = "ممارس تقني خبير في استخدام الأدوات المتخصصة والمجالات المجاورة في بيئات العمل الحقيقية"
            goal_prefix = "شرح الأداة أو المجال المجاور المتعلق بـ"
            constraint = "لا تصف الأداة بشكل عام، وضح بدقة كيف ترتبط بحالتي الخاصة وتقدم قيمة مضافة."
    else:  # contradiction
        role = "critical reviewer and risk analyst who challenges core assumptions"
        goal_prefix = "challenge the approach and stress-test the assumptions regarding"
        constraint = "Do not soften the problem or use diplomatic language, state the risks directly with their potential consequences."
        if lang == "ar":
            role = "مُراجع ناقد ومحلل مخاطر متخصص في تحدي الافتراضات الجوهرية"
            goal_prefix = "تحدي النهج الحالي واختبار مرونة الافتراضات المتعلقة بـ"
            constraint = "لا تخفف من حدة المشكلة أو تستخدم لغة ديبلوماسية، اذكر المخاطر مباشرة مع عواقبها المحتملة."

    # 2. GOAL
    if lang == "ar":
        goal = f"الهدف هو {goal_prefix} {missing}. هذا الأمر ضروري لأن: {why}."
        context_label = "السياق والمراجع:"
        constraints_label = "القيود والتعليمات:"
        output_label = "تنسيق المخرجات المطلوب:"
        no_generic = "لا تعطني نصائح عامة أو بديهية."
        no_repeat = "لا تكرر المعلومات التي تم ذكرها بالفعل في المحادثة."
        output_format = "قائمة مرقمة تحتوي على تحليل عميق، تليها خطوات تنفيذية محددة."
    else:
        goal = f"The goal is to {goal_prefix} {missing}. This is critical because: {why}."
        context_label = "Context and References:"
        constraints_label = "Constraints and Guidelines:"
        output_label = "Required Output Format:"
        no_generic = "Do not provide generic or obvious advice."
        no_repeat = "Do not repeat information already established in the conversation."
        output_format = "A numbered list containing deep analysis followed by specific actionable steps."

    # Build prompt
    prompt = (
        f"{'Act as a' if lang=='en' else 'قم بدور'} {role}.\n\n"
        f"{'Goal:' if lang=='en' else 'الهدف:'} {goal}\n\n"
        f"{context_label}\n"
        f"- {excerpt}\n"
        f"- {why}\n\n"
        f"{constraints_label}\n"
        f"- {no_generic}\n"
        f"- {no_repeat}\n"
        f"- {constraint}\n\n"
        f"{output_label}\n"
        f"{output_format}"
    )

    # Simple word count expansion to ensure 80+ words
    words = prompt.split()
    if len(words) < 80:
        extra = (
            " Ensure that the analysis is rigorous and evidence-based, providing a level of detail "
            "that goes beyond surface-level observations. Focus on structural integrity and "
            "practical implementation details that would be relevant to a senior professional."
            if lang == "en" else
            " تأكد من أن التحليل دقيق ومبني على الأدلة، مع تقديم مستوى من التفاصيل يتجاوز الملاحظات "
            "السطحية. ركز على السلامة الهيكلية وتفاصيل التنفيذ العملي التي قد تكون ذات صلة لمحترف خبير."
        )
        prompt += "\n\n" + extra

    return prompt


def build_prompts(
    classified_findings: dict,
    conversations_block: str,
    maps_context: str,
    lang: str
) -> dict:
    """Build ready_prompts for all classified findings.

    Args:
        classified_findings: dict with keys 'completion', 'alignment',
            'contradiction' — each a list of finding dicts.
        conversations_block: full compressed conversation text.
        maps_context: the maps context block (may be empty string).
        lang: "ar" or "en".

    Returns:
        Same classified_findings structure with ready_prompt on every finding.
    """
    completion = [_strip_ready_prompt(f) for f in classified_findings.get("completion", [])]
    alignment = [_strip_ready_prompt(f) for f in classified_findings.get("alignment", [])]
    contradiction = [_strip_ready_prompt(f) for f in classified_findings.get("contradiction", [])]

    conversations_excerpt = (conversations_block or "")[:1500]
    maps_ctx = maps_context or ""

    system = SYSTEM_PROMPT.replace("{lang}", lang)
    user = USER_PROMPT_TEMPLATE.format(
        conversations_excerpt=conversations_excerpt,
        maps_context=maps_ctx,
        completion_findings=json.dumps(completion, ensure_ascii=False),
        alignment_findings=json.dumps(alignment, ensure_ascii=False),
        contradiction_findings=json.dumps(contradiction, ensure_ascii=False),
    )

    if not OPENAI_API_KEY or "-key-" in OPENAI_API_KEY:
        return _apply_fallback(classified_findings, lang)

    client = OpenAI(api_key=OPENAI_API_KEY)
    last_error = "unknown"

    for attempt in range(2):
        try:
            res = client.chat.completions.create(
                model=PROMPT_ARCHITECT_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=0.2,
                max_completion_tokens=3000,
                response_format={"type": "json_object"}
            )
            text = res.choices[0].message.content
            print(f"[DEBUG] build_prompts SUCCESS. Raw response (first 100 chars): {text[:100]!r}")

            data = json.loads(text.strip())
            print(f"[DEBUG] Parsed JSON type: {type(data)}")

            # If model returned a flat list of findings, re-classify them
            if isinstance(data, list):
                new_data = {"completion": [], "alignment": [], "contradiction": []}
                for item in data:
                    cat = item.get("category", "").lower()
                    if not cat:
                        # Fallback mapping based on common type names
                        itype = item.get("type", "").lower()
                        cat = {
                            "informational": "completion",
                            "complementary": "alignment",
                            "inferential": "contradiction"
                        }.get(itype, "completion")
                    
                    if cat in new_data:
                        new_data[cat].append(item)
                    else:
                        new_data["completion"].append(item)
                data = new_data

            # Normalize: unwrap if model wrapped in an outer key
            if not isinstance(data, dict):
                raise ValueError(f"Expected dict or list, got {type(data)}")
            
            for wrapper_key in ("classified_findings", "findings"):
                inner = data.get(wrapper_key)
                if isinstance(inner, dict):
                    data = inner
                    break

            # Normalize category keys to lowercase and handle common misspellings
            normalized = {"completion": [], "alignment": [], "contradiction": []}
            for key, val in data.items():
                lk = key.lower()
                target = None
                if lk in ("completion", "informational"): target = "completion"
                elif lk in ("alignment", "complementary"): target = "alignment"
                elif lk in ("contradiction", "inferential", "contraction"): target = "contradiction"
                
                if target and isinstance(val, list):
                    normalized[target].extend(val)
            data = normalized

            # Ensure every original finding has a ready_prompt from the model or fallback
            result = {}
            for category in ("completion", "alignment", "contradiction"):
                result[category] = []
                original_list = classified_findings.get(category, [])
                model_list = data.get(category, [])
                
                for orig in original_list:
                    finding = dict(orig)
                    # Try to find matching finding in model response by missing_angle
                    match = None
                    for m in model_list:
                        if m.get("missing_angle") == orig.get("missing_angle"):
                            match = m
                            break
                    
                    if match and match.get("ready_prompt"):
                        finding["ready_prompt"] = match["ready_prompt"]
                    else:
                        # If no direct match, maybe the model just returned prompts in order?
                        pass

                    if not finding.get("ready_prompt"):
                        finding["ready_prompt"] = _build_fallback_prompt(finding, category, lang)
                    
                    result[category].append(finding)

            return result

        except Exception as e:
            last_error = str(e)
            print(f"[DEBUG] build_prompts FAILED. Error: {last_error}")
            # Wait 3 seconds before retry on rate limit
            if "rate" in last_error.lower() or "429" in last_error:
                import time
                time.sleep(3)
            continue

    # All retries failed — use fallback
    print(f"[prompt_architect] API failed after 2 attempts: {last_error}")
    return _apply_fallback(classified_findings, lang)


def _apply_fallback(classified_findings: dict, lang: str = "ar") -> dict:
    """Apply fallback prompts to all findings when the API fails."""
    result = {}
    for category in ("completion", "alignment", "contradiction"):
        findings = []
        for f in classified_findings.get(category, []):
            finding = dict(f)
            if not finding.get("ready_prompt"):
                finding["ready_prompt"] = _build_fallback_prompt(finding, category, lang)
            findings.append(finding)
        result[category] = findings
    return result
