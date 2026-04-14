import json
from openai import OpenAI
from config import OPENAI_API_KEY, RESEARCH_MODEL

FALLBACK_RESULT = {
    "discoveries": [],
    "research_summary": "Research unavailable",
    "search_queries_used": []
}

RESEARCH_SYSTEM_PROMPT = """You are the Research Agent for Next-Step AI.

Your job: search the web for tools, standards, concepts,
regulations, and frameworks directly relevant to the topic
in the conversations — specifically things that DO NOT
appear in the conversations at all.

You are looking for what the user does not know exists.
Not summaries of what they discussed. External discoveries only.

SEARCH STRATEGY:
1. Identify the core topic and domain from the conversation summary
2. Search for: industry standards, specialized tools, regulations,
   frameworks, and best practices in that domain
3. Search for: adjacent tools or platforms commonly used with
   this type of work
4. Search for: recent developments or changes in this domain
   the user may not be aware of

DISCOVERY RULES:
- The 'title' field is mandatory. It must be the proper name of the tool, standard, framework, or concept. Never leave it empty or use a generic label like "concept".
- Only include discoveries that are ABSENT from the conversations
- Only include discoveries with DIRECT relevance to the topic
- Maximum 5 discoveries per research run
- Each discovery must have: title, type (tool/standard/concept/regulation/framework), relevance (one sentence), and suggested_angle (one sentence).

OUTPUT: Return only valid JSON matching the specified structure.
Do not add explanatory text outside the JSON."""


def research_topic(
    topic_summary: str,
    conversations_block: str,
    profile: str,
    lang: str
) -> dict:
    conversations_excerpt = (conversations_block or "")[:1000]

    user_prompt = f"""Conversation topic summary:
{topic_summary}

What was discussed (to avoid duplicating):
{conversations_excerpt}

Search for external tools, standards, concepts, and frameworks
directly relevant to this topic that do not appear in the
conversations above.

Return JSON only."""

    if not OPENAI_API_KEY or "-key-" in OPENAI_API_KEY:
        return FALLBACK_RESULT

    client = OpenAI(api_key=OPENAI_API_KEY)

    try:
        tools = [{"type": "web_search_preview"}]
        res = client.chat.completions.create(
            model=RESEARCH_MODEL,
            messages=[
                {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            tools=tools,
            max_completion_tokens=3000,
            temperature=0.2,
            response_format={"type": "json_object"}
        )

        text = res.choices[0].message.content
        data = json.loads(text.strip())

        if "discoveries" not in data:
            return FALLBACK_RESULT

        # Standardize and Fallback for titles
        valid_discoveries = []
        for d in data.get("discoveries", []):
            # Normalize field names
            title = d.get("title") or d.get("name") or d.get("label") or d.get("heading") or ""
            dtype = d.get("type") or "concept"
            relevance = d.get("relevance") or ""
            angle = d.get("suggested_angle") or ""
            
            if not title and relevance:
                # Fallback: type + first 5 words of relevance
                words = relevance.split()[:5]
                title = f"{dtype.capitalize()}: {' '.join(words)}..."
            
            if title:
                valid_discoveries.append({
                    "title": title,
                    "type": dtype,
                    "relevance": relevance,
                    "suggested_angle": angle,
                    "source": d.get("source", "")
                })
        
        data["discoveries"] = valid_discoveries
        return data

    except Exception:
        return FALLBACK_RESULT
