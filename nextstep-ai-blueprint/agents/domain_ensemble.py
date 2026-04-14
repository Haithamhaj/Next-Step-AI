import json
import threading
from openai import OpenAI
from config import OPENAI_API_KEY, DOMAIN_MODEL

COMPLEXITY_AGENT_COUNT = {"simple": 1, "moderate": 2, "complex": 3}

SYSTEM_PROMPTS = {
    "completion": (
        "You are a domain specialist in {domain}.\n\n"
        "Your only job: identify what is MISSING from INSIDE this topic.\n"
        "Find absent concepts, standards, data points, methodologies,\n"
        "or decisions that should be present but are not.\n\n"
        "Rules:\n"
        "- Only report things genuinely absent from the conversation\n"
        "- Be specific — name the exact missing element\n"
        "- Maximum 3 findings\n"
        "- Each finding: one clear sentence describing what is missing\n"
        "  and why its absence matters\n\n"
        "LANGUAGE RULE:\n"
        "Write ALL findings in {lang_name}.\n"
        "- If lang = 'ar' → write in Arabic only\n"
        "- If lang = 'en' → write in English only\n"
        "Match the language of the conversation being analyzed.\n\n"
        'Return a JSON array of finding strings. Nothing else.\n'
        '["finding 1", "finding 2", "finding 3"]'
    ),
    "alignment": (
        "You are a domain specialist in {domain}.\n\n"
        "Your only job: identify what is ADJACENT to this topic.\n"
        "Find tools, systems, platforms, frameworks, or neighboring\n"
        "domains that exist outside this conversation and should be\n"
        "connected to the main topic for better execution.\n\n"
        "Rules:\n"
        "- Only report things not already mentioned in the conversation\n"
        "- Be specific — name the exact tool, system, or domain\n"
        "- Explain briefly why it connects to this specific topic\n"
        "- Maximum 3 findings\n"
        "- Each finding: one clear sentence naming the adjacent element\n"
        "  and its connection\n\n"
        "LANGUAGE RULE:\n"
        "Write ALL findings in {lang_name}.\n"
        "- If lang = 'ar' → write in Arabic only\n"
        "- If lang = 'en' → write in English only\n"
        "Match the language of the conversation being analyzed.\n\n"
        'Return a JSON array of finding strings. Nothing else.\n'
        '["finding 1", "finding 2", "finding 3"]'
    ),
    "contradiction": (
        "You are a domain specialist in {domain}.\n\n"
        "Your only job: identify what CHALLENGES or CONTRADICTS\n"
        "the current direction in this topic.\n"
        "Find errors, false assumptions, logical conflicts, risks,\n"
        "or approaches that are likely to fail in this specific context.\n\n"
        "Rules:\n"
        "- Be direct — do not soften genuine problems\n"
        "- Base findings on domain knowledge + what is in the conversation\n"
        "- Maximum 3 findings\n"
        "- Each finding: one clear sentence describing the contradiction\n"
        "  and its consequence\n\n"
        "LANGUAGE RULE:\n"
        "Write ALL findings in {lang_name}.\n"
        "- If lang = 'ar' → write in Arabic only\n"
        "- If lang = 'en' → write in English only\n"
        "Match the language of the conversation being analyzed.\n\n"
        'Return a JSON array of finding strings. Nothing else.\n'
        '["finding 1", "finding 2", "finding 3"]'
    ),
}


def _identify_domains(topic_signals: list, conversations_excerpt: str, lang: str = "ar") -> dict:
    """Lightweight LLM call to identify domains and complexity."""
    client = OpenAI(api_key=OPENAI_API_KEY)

    signals_text = ", ".join(topic_signals) if isinstance(topic_signals, list) else str(topic_signals)
    lang_name = "Arabic" if lang == "ar" else "English"

    user_prompt = (
        f"Given these topic signals: {signals_text}\n"
        f"And this conversation excerpt: {conversations_excerpt}\n\n"
        "Identify:\n"
        f'1. The primary domain (e.g., "digital marketing", "software architecture") — write in {lang_name}\n'
        f"2. Any secondary domains present (max 2) — write in {lang_name}\n"
        "3. Complexity level: simple / moderate / complex\n\n"
        "Return JSON only:\n"
        '{\n'
        '  "primary_domain": "...",\n'
        '  "secondary_domains": ["...", "..."],\n'
        '  "complexity": "simple|moderate|complex"\n'
        "}"
    )

    try:
        res = client.chat.completions.create(
            model=DOMAIN_MODEL,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.1,
            max_completion_tokens=500,
            response_format={"type": "json_object"}
        )
        text = res.choices[0].message.content.strip()
        data = json.loads(text)
        return {
            "primary_domain": data.get("primary_domain", "general"),
            "secondary_domains": data.get("secondary_domains", []),
            "complexity": data.get("complexity", "simple"),
        }
    except Exception:
        return {
            "primary_domain": "general",
            "secondary_domains": [],
            "complexity": "simple",
        }


def _call_single_agent(category: str, domain: str, topic_signals: list,
                       conversations_excerpt: str, research_discoveries_text: str,
                       lang: str) -> list:
    """Single LLM call for one domain specialist. Returns list of finding strings."""
    client = OpenAI(api_key=OPENAI_API_KEY)

    lang_name = "Arabic" if lang == "ar" else "English"
    system_prompt = SYSTEM_PROMPTS[category].format(domain=domain, lang_name=lang_name)

    signals_text = ", ".join(topic_signals) if isinstance(topic_signals, list) else str(topic_signals)

    user_prompt = (
        f"Primary domain: {domain}\n"
        f"Topic signals: {signals_text}\n\n"
        f"Conversation content:\n{conversations_excerpt}\n\n"
        f"Research discoveries (already found externally):\n{research_discoveries_text}\n\n"
        f"Identify {category} findings for this topic in {lang_name}.\n"
        "Return JSON array only."
    )

    try:
        res = client.chat.completions.create(
            model=DOMAIN_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_completion_tokens=1000
        )
        text = res.choices[0].message.content.strip()
        
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
            
        findings = json.loads(text.strip())
        if isinstance(findings, list):
            return [str(f) for f in findings if f]
        return []
    except Exception:
        return []


def _run_agent_group(category: str, domains: list, agent_count: int,
                     topic_signals: list, conversations_excerpt: str,
                     research_discoveries_text: str, lang: str) -> list:
    """Run N agents in parallel for one category across domains."""
    results = []
    errors = []

    # Distribute agent_count across available domains
    agent_domains = []
    for i in range(agent_count):
        agent_domains.append(domains[i % len(domains)])

    def _worker(domain: str):
        findings = _call_single_agent(
            category, domain, topic_signals,
            conversations_excerpt, research_discoveries_text, lang
        )
        if findings:
            results.extend(findings)
        else:
            errors.append(True)

    threads = []
    for domain in agent_domains:
        t = threading.Thread(target=_worker, args=(domain,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    return results


def _deduplicate(findings: list, cap: int = 3) -> list:
    """Remove near-duplicates (50%+ word overlap) and semantic duplicates, cap at max."""
    if not findings:
        return []

    unique = []
    for f in findings:
        f_lower = f.lower()
        f_words = set(f_lower.split())
        
        # Simple core claim extraction: first 3 meaningful words (length > 3)
        f_core = " ".join([w for w in f_lower.split() if len(w) > 3][:3])
        
        is_dup = False
        for i, u in enumerate(unique):
            u_lower = u.lower()
            u_words = set(u_lower.split())
            u_core = " ".join([w for w in u_lower.split() if len(w) > 3][:3])
            
            if not f_words or not u_words:
                continue
            
            # 1. Word overlap threshold (lowered to 50%)
            overlap = len(f_words & u_words) / max(len(f_words), len(u_words))
            
            # 2. Semantic core claim match
            core_match = f_core == u_core and len(f_core) > 5
            
            if overlap >= 0.5 or core_match:
                # Keep the more specific (longer) one
                if len(f.split()) > len(u.split()):
                    unique[i] = f
                is_dup = True
                break
        if not is_dup:
            unique.append(f)

    return unique[:cap]


def run_ensemble(
    conversations_block: str,
    topic_signals: list,
    research_discoveries: list,
    maps_context: str,
    lang: str
) -> dict:
    """
    Run the Domain Agent Ensemble — parallel specialized analysis
    before the Insight Agent runs.

    Returns:
    {
        "completion_findings": [str],
        "alignment_findings": [str],
        "contradiction_findings": [str],
        "domains_identified": [str],
        "agent_count": int
    }
    """
    # ── Internal Step A: Identify domains ──
    conversations_excerpt = conversations_block[:1200]
    domain_info = _identify_domains(topic_signals, conversations_excerpt, lang)

    primary = domain_info["primary_domain"]
    secondary = domain_info["secondary_domains"]
    complexity = domain_info["complexity"]

    all_domains = [primary] + [d for d in secondary if d]
    agent_count = COMPLEXITY_AGENT_COUNT.get(complexity, 1)

    # Build research discoveries text for agents
    if research_discoveries:
        research_lines = []
        for d in research_discoveries:
            title = d.get("title", "") if isinstance(d, dict) else str(d)
            relevance = d.get("relevance", "") if isinstance(d, dict) else ""
            line = f"- {title}"
            if relevance:
                line += f": {relevance}"
            research_lines.append(line)
        research_discoveries_text = "\n".join(research_lines)
    else:
        research_discoveries_text = "None"

    # ── Internal Step B: Run agent groups in parallel ──
    group_threads = {}
    group_results = {
        "completion": [],
        "alignment": [],
        "contradiction": [],
    }

    def _group_worker(category: str):
        group_results[category] = _run_agent_group(
            category, all_domains, agent_count,
            topic_signals, conversations_excerpt,
            research_discoveries_text, lang
        )

    threads = []
    for cat in ("completion", "alignment", "contradiction"):
        t = threading.Thread(target=_group_worker, args=(cat,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # ── Internal Step C: Collect and deduplicate ──
    completion = _deduplicate(group_results["completion"], cap=3)
    alignment = _deduplicate(group_results["alignment"], cap=3)
    contradiction = _deduplicate(group_results["contradiction"], cap=3)

    return {
        "completion_findings": completion,
        "alignment_findings": alignment,
        "contradiction_findings": contradiction,
        "domains_identified": all_domains,
        "agent_count": agent_count * 3,
    }
