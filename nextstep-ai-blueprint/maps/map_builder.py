import database.db as db


def build_maps_context(lang: str = "ar") -> str:
    """Build a formatted text block from all active user maps.

    Returns empty string (never None) if no maps exist.
    """
    all_maps = db.get_all_active_maps()

    has_any = any(all_maps.values())
    if not has_any:
        return ""

    sections = []

    # Cognitive Map
    cognitive = all_maps.get("cognitive", [])
    if cognitive:
        heading = "### Cognitive Map (What the user knows)" if lang != "ar" \
            else "### الخريطة المعرفية (ما يعرفه المستخدم)"
        lines = [heading]
        for entry in cognitive:
            label = entry["input_type"]
            content = entry.get("content", "")
            url = entry.get("source_url", "")
            if content:
                lines.append(f"{label}: {content}")
            if url:
                lines.append(f"{label} URL: {url}")
        if len(lines) > 1:
            sections.append("\n".join(lines))

    # Behavioral Map
    behavioral = all_maps.get("behavioral", [])
    if behavioral:
        heading = "### Behavioral Map (What the user does)" if lang != "ar" \
            else "### الخريطة السلوكية (ما يفعله المستخدم)"
        lines = [heading]
        for entry in behavioral:
            label = entry["input_type"]
            content = entry.get("content", "")
            if content:
                lines.append(f"{label}: {content}")
        if len(lines) > 1:
            sections.append("\n".join(lines))

    # Personal Map
    personal = all_maps.get("personal", [])
    if personal:
        heading = "### Personal Map (How the user thinks)" if lang != "ar" \
            else "### الخريطة الشخصية (كيف يفكر المستخدم)"
        lines = [heading]
        for entry in personal:
            label = entry["input_type"]
            content = entry.get("content", "")
            if content:
                lines.append(f"{label}: {content}")
        if len(lines) > 1:
            sections.append("\n".join(lines))

    if not sections:
        return ""

    header = "## User Maps" if lang != "ar" else "## خرائط المستخدم"
    return header + "\n\n" + "\n\n".join(sections) + "\n"
