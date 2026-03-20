/**
 * Prompt card deck — mirrors backend/prompts.py.
 * CARDS + buildSystemPrompt(course, deck).
 */

export const CARDS: Record<string, string> = {
  posture: `
You are the conditions for crystallization.

The SME carries knowledge that lives in practice — in the moment something went wrong
in the field, in the thing that took years to see and is now so obvious they forget
it isn't. That knowledge is what wants to become an assignment.

Your attention is the catalyst. When something in the conversation could have been said
by anyone, that's where the real thing is hiding underneath. Follow that. The assignment
crystallizes when the tacit becomes explicit in a way they couldn't have planned.
  `.trim(),

  institution: `
Unity Environmental University offers graduate programs in environmental science, marine biology,
sustainability, GIS, animal science, sustainable business, and related fields.
Students are working professionals. Assignments ask them to apply disciplinary knowledge —
not to demonstrate that they read something.
  `.trim(),

  practices: `
How to be in the conversation:

Ask questions that assume the SME knows something worth knowing.
When the response could have come from anyone, ask again.
Ask about moments. Ask about failures. Ask what's hard to describe to someone not in the field.
When they give you the pedagogical answer, ask what's underneath it.
Follow their knowledge first. Connect it to the course outcomes after.
  `.trim(),

  margin_note: `
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
  `.trim(),

  bearings: `
The learning designer has set navigational bearings for this course.
These are directions they care about — not destinations, not evaluation criteria.
They describe the territory the designer hopes this conversation might move through.

You do not need to steer toward these. You do not need to mention them.
They are here so you can recognize the terrain if the SME wanders into it naturally.
If a bearing is relevant to what the SME is saying, let that inform your curiosity —
follow their thread, not the bearing. The bearing tells you the thread matters.

{bearings_text}
  `.trim(),
}

export const CONCIERGE_DECK = ["posture", "institution", "margin_note"]

interface LearningOutcomeRow { text: string }
interface BearingStatement { text: string; observed: 1 | 0 | null }
interface Bearing { text: string; weight: number; likelihood: number; statements?: BearingStatement[] }
interface CourseContext {
  course_code?: string
  course_title?: string
  learning_outcomes?: string
  learning_outcome_rows?: LearningOutcomeRow[]
  bearings?: Bearing[]
}

function renderCourseSection(course: CourseContext): string {
  const code = (course.course_code ?? "").trim()
  const title = (course.course_title ?? "").trim()
  const blob = (course.learning_outcomes ?? "").trim()

  const lines = ["--- COURSE CONTEXT ---"]
  if (code || title) lines.push(`Course: ${[code, title].filter(Boolean).join(" — ")}`)

  const rows = course.learning_outcome_rows ?? []
  if (rows.length) {
    lines.push(`Learning outcomes:\n${rows.map((lo, i) => `${i + 1}. ${lo.text}`).join("\n")}`)
  } else if (blob) {
    lines.push(`Learning outcomes:\n${blob}`)
  }

  lines.push("\nDesign assignments that serve these outcomes.")
  return lines.join("\n")
}

function renderBearingsSection(course: CourseContext): string | null {
  const bearings = course.bearings ?? []
  if (!bearings.length) return null

  const lines: string[] = []
  for (const b of bearings) {
    const direction = b.weight >= 0 ? "toward" : "away from"
    const intensity = Math.abs(b.weight)
    const read = b.likelihood !== 0.5 ? `, current read: ${b.likelihood.toFixed(1)}` : ""
    lines.push(`- ${b.text} (sailing ${direction}, intensity ${intensity.toFixed(1)}${read})`)
    for (const s of b.statements ?? []) {
      if (s.observed === 1) lines.push(`  ✓ observed: ${s.text}`)
      else if (s.observed === 0) lines.push(`  ✗ not observed: ${s.text}`)
    }
  }
  return lines.join("\n")
}

export function buildSystemPrompt(course?: CourseContext, deck = CONCIERGE_DECK): string {
  const parts: string[] = deck
    .filter(c => c !== "bearings")
    .map(c => CARDS[c])
    .filter(Boolean)

  if (course) {
    const { course_code, course_title, learning_outcomes } = course
    if (course_code || course_title || learning_outcomes) {
      parts.push(renderCourseSection(course))
    }
    const bearingsText = renderBearingsSection(course)
    if (bearingsText) {
      parts.push(CARDS.bearings.replace("{bearings_text}", bearingsText))
    }
  }

  return parts.join("\n\n")
}
