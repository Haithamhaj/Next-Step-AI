import json
import anthropic
from config import ANTHROPIC_API_KEY, INSIGHT_MODEL

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
- Only include discoveries that are ABSENT from the conversations
- Only include discoveries with DIRECT relevance to the topic
- Do not include general knowledge or obvious facts
- Do not include anything already mentioned in the conversations
- Maximum 5 discoveries per research run
- Each discovery must have a clear suggested_angle — how it
  could open a door for the user

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

    if not ANTHROPIC_API_KEY or "-key-" in ANTHROPIC_API_KEY:
        return FALLBACK_RESULT

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    try:
        res = client.messages.create(
            model=INSIGHT_MODEL,
            max_tokens=3000,
            temperature=0.2,
            system=RESEARCH_SYSTEM_PROMPT,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 5
            }],
            messages=[{"role": "user", "content": user_prompt}]
        )

        text = ""
        for block in res.content:
            if block.type == "text":
                text += block.text

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        data = json.loads(text.strip())

        if "discoveries" not in data:
            return FALLBACK_RESULT

        return data

    except Exception:
        return FALLBACK_RESULT
