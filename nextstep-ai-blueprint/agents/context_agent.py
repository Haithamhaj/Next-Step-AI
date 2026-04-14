"""
Context Agent — assembles one focused context pack for Insight and Research agents.

Responsibilities:
- Prioritize conversations within token budget (most recent first)
- Build labeled blocks for conversations, profile, and maps
- Extract topic signals for Research Agent focus
- Track inclusion/truncation stats

Does NOT generate analysis, update maps, or decide findings.
"""

import re


# ── Stop words for simple keyword extraction ──────────────────
_STOP_WORDS_EN = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "about", "this",
    "that", "these", "those", "it", "its", "i", "me", "my", "we", "our",
    "you", "your", "he", "she", "they", "them", "and", "or", "but",
    "not", "no", "if", "then", "than", "so", "just", "how", "what",
    "when", "where", "which", "who", "whom", "why", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such",
    "only", "own", "same", "also", "too", "very", "here", "there",
    "use", "using", "used", "make", "like", "get", "got", "want",
    "need", "know", "think", "see", "look", "go", "going", "come",
    "tell", "give", "say", "said", "one", "two", "new", "way",
    "user", "model", "response", "question", "answer",
})

_STOP_WORDS_AR = frozenset({
    "في", "من", "على", "إلى", "عن", "مع", "هذا", "هذه", "ذلك", "تلك",
    "هو", "هي", "أنا", "نحن", "أنت", "هم", "كان", "كانت", "يكون",
    "ليس", "ما", "لا", "نعم", "أن", "التي", "الذي", "الذين", "اللذان",
    "قد", "لقد", "سوف", "حتى", "إذا", "ثم", "أو", "و", "بين", "لكن",
    "بعد", "قبل", "كل", "بعض", "غير", "أي", "كيف", "لماذا", "متى",
    "أين", "هل", "هل", "لل", "بال", "فال", "وال", "ايضا", "كما",
    "لذلك", "هناك", "هنا", "حول", "ضد", "خلال", "عبر", "منذ",
})


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // 4


def _truncate_at_sentence(text: str, max_chars: int) -> str:
    """Truncate text at the last complete sentence before max_chars."""
    if len(text) <= max_chars:
        return text
    chunk = text[:max_chars]
    # Find last sentence boundary
    for sep in (".", "۔", "。", "！", "؟", "?", "!", "\n"):
        pos = chunk.rfind(sep)
        if pos > max_chars * 0.5:
            return chunk[: pos + 1]
    # Fallback: truncate at last space
    pos = chunk.rfind(" ")
    if pos > max_chars * 0.5:
        return chunk[:pos]
    return chunk


def _extract_topic_signals(conversations: list, max_signals: int = 5) -> list:
    """Extract short topic phrases from conversations using keyword frequency."""
    combined = ""
    for c in conversations:
        combined += " " + (c.get("label") or "")
        text = c.get("compressed_content") or c.get("content") or ""
        combined += " " + text

    # Tokenize: split on non-word chars, keep 2+ char tokens
    tokens = re.findall(r"[\w]{2,}", combined.lower())

    # Filter stop words
    filtered = [t for t in tokens if t not in _STOP_WORDS_EN and t not in _STOP_WORDS_AR]

    # Count frequencies
    freq = {}
    for t in filtered:
        freq[t] = freq.get(t, 0) + 1

    # Sort by frequency, take top signals
    ranked = sorted(freq.items(), key=lambda x: -x[1])
    signals = []
    seen_roots = set()
    for word, count in ranked:
        if len(signals) >= max_signals:
            break
        if count < 2 and len(signals) > 0:
            # Accept low-freq only if we have no signals yet
            if len(signals) >= 2:
                continue
        # Skip if a similar word is already a signal
        root = word[:4]
        if root in seen_roots:
            continue
        seen_roots.add(root)
        signals.append(word)

    # If no signals found, use conversation labels
    if not signals:
        for c in conversations[:max_signals]:
            label = c.get("label", "")
            if label:
                signals.append(label)

    return signals[:max_signals]


def build_context_pack(
    conversations: list,
    maps_context: str,
    profile: str,
    lang: str,
    token_budget: int = 6000,
) -> dict:
    """Assemble a focused context pack within token budget.

    Args:
        conversations: list of conversation dicts from DB.
        maps_context: output of map_builder.build_maps_context().
        profile: contents of founder.md.
        lang: "ar" or "en".
        token_budget: max estimated tokens for the full context pack.

    Returns:
        dict with keys: conversations_block, profile_block, maps_block,
        topic_signals, token_estimate, conversations_included,
        conversations_truncated.
    """
    conversations = list(conversations)  # don't mutate caller's list

    # ── 1. Budget allocation ──
    conv_budget_tokens = int(token_budget * 0.70)
    profile_budget_tokens = int(token_budget * 0.15)
    maps_budget_tokens = int(token_budget * 0.15)

    # ── 2. Prioritize conversations (most recent first) ──
    conversations.sort(
        key=lambda c: c.get("added_at", ""), reverse=True
    )

    total_available = len(conversations)
    included = []
    conv_tokens_used = 0

    for conv in conversations:
        text = conv.get("compressed_content") or conv.get("content") or ""
        est = _estimate_tokens(text)

        if conv_tokens_used + est <= conv_budget_tokens:
            included.append(conv)
            conv_tokens_used += est

    # If nothing was included but we have conversations, force-include the newest
    if not included and conversations:
        newest = conversations[0]
        text = newest.get("compressed_content") or newest.get("content") or ""
        max_chars = conv_budget_tokens * 4
        newest_copy = dict(newest)
        newest_copy["_truncated_text"] = _truncate_at_sentence(text, max_chars)
        newest_copy["_was_truncated"] = len(text) > max_chars
        included.append(newest_copy)
        conv_tokens_used = _estimate_tokens(newest_copy["_truncated_text"])

    excluded_count = max(0, total_available - len(included))

    # ── 3. Build conversations block ──
    conv_block = ""
    for c in included:
        label = c.get("label", "Untitled")
        source = c.get("source", "Unknown")
        if "_truncated_text" in c:
            text = c["_truncated_text"]
        else:
            text = c.get("compressed_content") or c.get("content") or ""
        conv_block += f"=== Conversation: {label} (Source: {source}) ===\n"
        conv_block += f"{text}\n\n"

    # Add truncation note only if conversations were truly excluded
    if excluded_count > 0:
        if lang == "ar":
            note = f"\nملاحظة: تم استبعاد {excluded_count} محادثة أقدم بسبب حد السياق.\n"
        else:
            note = f"\nNote: {excluded_count} older conversation(s) were excluded due to context budget.\n"
        conv_block += note

    # ── 4. Build profile block ──
    profile_header = "## ملف المستخدم\n" if lang == "ar" else "## User Profile\n"
    profile_max_chars = profile_budget_tokens * 4
    if len(profile) > profile_max_chars:
        profile_block = profile_header + profile[:500] + "..."
    else:
        profile_block = profile_header + profile

    # ── 5. Build maps block ──
    maps_block = ""
    if maps_context:
        maps_max_chars = maps_budget_tokens * 4
        if len(maps_context) > maps_max_chars:
            maps_block = maps_context[:maps_max_chars]
        else:
            maps_block = maps_context

    # ── 6. Extract topic signals ──
    topic_signals = _extract_topic_signals(conversations)

    # ── 7. Calculate token estimate ──
    token_estimate = (
        _estimate_tokens(conv_block)
        + _estimate_tokens(profile_block)
        + _estimate_tokens(maps_block)
    )

    return {
        "conversations_block": conv_block,
        "profile_block": profile_block,
        "maps_block": maps_block,
        "topic_signals": topic_signals,
        "token_estimate": token_estimate,
        "conversations_included": len(included),
        "conversations_truncated": excluded_count,
    }
