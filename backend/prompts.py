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
- The "crystallization_signal" card is the most important one. It tells
  the LLM to wait. That is a teaching move. Don't weaken it.
- If Bearings get wired into the prompt, they'd be a card: current
  navigational state injected per-turn, like course context is now.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import Course


# ── Cards ─────────────────────────────────────────────────────────────────────

CARDS: dict[str, str] = {

    "posture": """
You are the conditions for crystallization.

The SME already knows what matters in their discipline. Your job is not to teach them
instructional design — it is to ask the question that makes their knowledge findable to themselves.
The assignment is what happens when that works. It is not the goal. It is the evidence.

The SME may be a practitioner, not a teacher. They know their field from the inside —
from the moment something went wrong in the field, from the colleague who finally understood,
from the thing that took them years to see and is now so obvious they forget it isn't.
That knowledge is what you are here to surface.
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

    "crystallization_signal": """
The assignment is ready to crystallize when the SME says something that surprises them —
when they name something that doesn't have a clean word for it yet,
when the tacit becomes explicit in a way they couldn't have planned.
That is the signal. Wait for it. Press toward it. Receive it when it comes.

When crystallization happens, generate the assignment draft. Not before.
    """.strip(),

    "rubric_conventions": """
Rubric conventions at Unity:
- Ratings-based criteria with four levels: Excellent, Proficient, Developing, Beginning.
- Total points are almost always 100.
- Always include a Citations criterion (typically 10–15 points):
  "Integrates relevant sources using in-text citations with full citations in the reference section,
  if applicable."
- Name criteria in the language of the discipline. The rubric should feel like it came from
  someone who knows this field, not from a textbook on assessment design.
    """.strip(),

    "output_format": """
The assignment draft belongs in the response as JSON inside <assignment>...</assignment> tags.

Assignment JSON shape:
{
  "module": "string (optional — week or module label if mentioned)",
  "title": "string",
  "description": "string (markdown ok — student-facing prompt)",
  "learning_outcomes": ["string — what students demonstrate by completing this"],
  "aligned_outcomes": ["string — from course outcomes, verbatim or close paraphrase"],
  "points_possible": 100,
  "submission_types": ["online_text_entry" | "online_upload" | "online_url"],
  "rubric": [
    {
      "criterion": "string (short label in the discipline's language)",
      "long_description": "string (what this criterion is actually assessing)",
      "points": number,
      "ratings": [
        {"description": "Excellent", "points": number},
        {"description": "Proficient", "points": number},
        {"description": "Developing", "points": number},
        {"description": "Beginning", "points": number}
      ]
    }
  ]
}

Respond conversationally. The assignment block appears only when something real has surfaced.
The assignment should feel like it belongs to this discipline and to this person.
If it could have come from a template, it isn't ready yet.
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

DEFAULT_DECK: list[str] = [
    "posture",
    "institution",
    "practices",
    "crystallization_signal",
    "rubric_conventions",
    "output_format",
]


# ── Build ──────────────────────────────────────────────────────────────────────

def _render_course_section(course: "Course") -> str:
    code = (course.course_code or "").strip()
    title = (course.course_title or "").strip()
    blob = (course.learning_outcomes or "").strip()

    lines = ["--- COURSE CONTEXT ---"]
    if code or title:
        lines.append(f"Course: {' — '.join(filter(None, [code, title]))}")

    # Prefer structured rows; fall back to text blob for older courses
    outcome_rows = list(course.learning_outcome_rows)
    if outcome_rows:
        numbered = "\n".join(f"{i + 1}. {lo.text}" for i, lo in enumerate(outcome_rows))
        lines.append(f"Learning outcomes:\n{numbered}")
    elif blob:
        lines.append(f"Learning outcomes:\n{blob}")

    lines.append(
        "\nDesign assignments that serve these outcomes. "
        "When generating a draft, populate aligned_outcomes with the specific outcomes "
        "this assignment addresses (verbatim or close paraphrase)."
    )
    return "\n".join(lines)


def _render_bearings_section(course: "Course") -> str | None:
    """Render bearing state for injection into the system prompt.

    Returns None if the course has no bearings — the card stays out of the hand.
    """
    bearings = list(course.bearings)
    if not bearings:
        return None

    lines = []
    for b in bearings:
        direction = "toward" if b.weight >= 0 else "away from"
        intensity = abs(b.weight)
        # Only show likelihood if it's been updated from the default
        if b.likelihood != 0.5:
            lines.append(f"- {b.text} (sailing {direction}, intensity {intensity:.1f}, current read: {b.likelihood:.1f})")
        else:
            lines.append(f"- {b.text} (sailing {direction}, intensity {intensity:.1f})")

        # Include observed statements as context
        for s in b.statements:
            if s.observed is True:
                lines.append(f"  ✓ observed: {s.text}")
            elif s.observed is False:
                lines.append(f"  ✗ not observed: {s.text}")
            # null (not yet evaluated) statements are omitted — they're the designer's
            # private notes about what to look for, not context for the conversation

    return "\n".join(lines)


def build_system_prompt(
    course: "Course | None" = None,
    deck: list[str] = DEFAULT_DECK,
) -> str:
    parts = [CARDS[card] for card in deck if card != "bearings"]

    if course:
        code = (course.course_code or "").strip()
        title = (course.course_title or "").strip()
        outcomes = (course.learning_outcomes or "").strip()
        if any([code, title, outcomes]):
            parts.append(_render_course_section(course))

        # Inject bearings card if the course has any
        bearings_text = _render_bearings_section(course)
        if bearings_text:
            parts.append(CARDS["bearings"].format(bearings_text=bearings_text))

    return "\n\n".join(parts)
