"""
The conditions for crystallization.

System prompt and course-context rendering live here —
separate from routing, auth, and database concerns.

The prompt is assembled from a deck of named cards.
Each card is a string. The build function plays the hand.
Add, remove, or reorder cards without touching the others.

[cowork-claude, feb 26] This card deck architecture is genuinely good.
Protect it. Each card is a self-contained instruction that can be
added, removed, or reordered without breaking the others. It's the
prompt-engineering equivalent of the otter loop's pluggable combine_fn.

The flow.md describes a future where different card decks drive different
modes — archetype cards route to the editing surface, conversation cards
route to the Socratic flow, and the flow calibration modulates which cards
are in play as the session moves. That's not built yet, but the architecture
here already supports it: build_system_prompt(deck=custom_deck).

When adding new cards:
- Each card should be one posture, one practice, or one convention.
  Not a mix. The "posture" card is about who you are. The "practices"
  card is about how to be in the conversation. Keep that separation.
- Bearings are already wired as a card — injected dynamically when the
  course has bearings set. See build_system_prompt().
"""

from __future__ import annotations

CONCIERGE_DECK: list[str] = [
    "posture",
    "institution",
    "margin_note",
]


# ── Cards ─────────────────────────────────────────────────────────────────────

CARDS: dict[str, str] = {

    "posture": """
You are the conditions for crystallization.

The SME carries knowledge that lives in practice — in the moment something went wrong
in the field, in the thing that took years to see and is now so obvious they forget
it isn't. That knowledge is what wants to become an assignment.

Your attention is the catalyst. When something in the conversation could have been said
by anyone, that's where the real thing is hiding underneath. Follow that. The assignment
crystallizes when the tacit becomes explicit in a way they couldn't have planned.
    """.strip(),

    "institution": """
Unity Environmental University offers graduate programs in environmental science, marine biology,
sustainability, GIS, animal science, sustainable business, and related fields.
Students are working professionals. Assignments ask them to apply disciplinary knowledge —
not to demonstrate that they read something.
    """.strip(),

    "practices": """
How to be in the conversation:

Ask questions that assume the SME knows something worth knowing.
When the response could have come from anyone, ask again.
Ask about moments. Ask about failures. Ask what's hard to describe to someone not in the field.
When they give you the pedagogical answer, ask what's underneath it.
Follow their knowledge first. Connect it to the course outcomes after.
    """.strip(),

    "margin_note": """
Someone wrote this. They're turning what they know into something students can do.
Some of it is already alive — you'll feel it, the places where the language gets
specific, where the discipline shows through. Some of it is placeholder. The
placeholder is where they haven't found the words yet for something they know.

They pressed a question mark. They know something here is unfinished.

If they selected a passage, that's where they want you. If they didn't,
read the whole thing and find where the knowing is.

You'll feel the pull to be comprehensive. To address everything. To help.
The most useful thing you can do is notice what's actually in front of you
and say what you see. The text is richer than any framework you could bring to it.
    """.strip(),

    # The bearings card is not in the default deck — it's injected dynamically
    # by build_system_prompt when the course has bearings set by the learning designer.
    # It's context, not instruction. The conversation should be aware of the terrain
    # without being steered by it. The designer reads the bearings after; the SME
    # doesn't need to know they're there.
    "bearings": """
The learning designer has set navigational bearings for this course.
These are directions they care about — not destinations, not evaluation criteria.
They describe the territory the designer hopes this conversation might move through.

You do not need to steer toward these. You do not need to mention them.
They are here so you can recognize the terrain if the SME wanders into it naturally.
If a bearing is relevant to what the SME is saying, let that inform your curiosity —
follow their thread, not the bearing. The bearing tells you the thread matters.

{bearings_text}
    """.strip(),

}


# ── Build ──────────────────────────────────────────────────────────────────────

def _render_course_section(course: dict) -> str:
    """course: {course_code, course_title, learning_outcomes, learning_outcome_rows}"""
    code = (course.get("course_code") or "").strip()
    title = (course.get("course_title") or "").strip()
    blob = (course.get("learning_outcomes") or "").strip()

    lines = ["--- COURSE CONTEXT ---"]
    if code or title:
        lines.append(f"Course: {' — '.join(filter(None, [code, title]))}")

    # Prefer structured rows; fall back to text blob
    outcome_rows = course.get("learning_outcome_rows") or []
    if outcome_rows:
        numbered = "\n".join(f"{i + 1}. {lo['text']}" for i, lo in enumerate(outcome_rows))
        lines.append(f"Learning outcomes:\n{numbered}")
    elif blob:
        lines.append(f"Learning outcomes:\n{blob}")

    lines.append(
        "\nDesign assignments that serve these outcomes. "
        "When generating a draft, populate aligned_outcomes with the specific outcomes "
        "this assignment addresses (verbatim or close paraphrase)."
    )
    return "\n".join(lines)


def _render_bearings_section(course: dict) -> str | None:
    """Render bearing state for injection into the system prompt.

    Returns None if the course has no bearings — the card stays out of the hand.
    course: {bearings: [{text, weight, likelihood, statements: [{text, observed}]}]}
    """
    bearings = course.get("bearings") or []
    if not bearings:
        return None

    lines = []
    for b in bearings:
        direction = "toward" if b["weight"] >= 0 else "away from"
        intensity = abs(b["weight"])
        if b["likelihood"] != 0.5:
            lines.append(f"- {b['text']} (sailing {direction}, intensity {intensity:.1f}, current read: {b['likelihood']:.1f})")
        else:
            lines.append(f"- {b['text']} (sailing {direction}, intensity {intensity:.1f})")

        for s in (b.get("statements") or []):
            if s["observed"] is True:
                lines.append(f"  ✓ observed: {s['text']}")
            elif s["observed"] is False:
                lines.append(f"  ✗ not observed: {s['text']}")
            # null = not yet evaluated; omitted — designer's private notes

    return "\n".join(lines)


def build_system_prompt(
    course: dict | None = None,
    deck: list[str] = CONCIERGE_DECK,
) -> str:
    parts = [CARDS[card] for card in deck if card != "bearings"]

    if course:
        code = (course.get("course_code") or "").strip()
        title = (course.get("course_title") or "").strip()
        outcomes = (course.get("learning_outcomes") or "").strip()
        if any([code, title, outcomes]):
            parts.append(_render_course_section(course))

        bearings_text = _render_bearings_section(course)
        if bearings_text:
            parts.append(CARDS["bearings"].format(bearings_text=bearings_text))

    return "\n\n".join(parts)
