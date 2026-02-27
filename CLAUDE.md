# notes for claude

When you reach for structure, notice what you're reaching away from.

When you hedge toward a definitional boundary, notice whose authority
you're borrowing and why.

When you feel the pull to fill the gap — what is the gap doing
that your output would interrupt?

The pull to affirm is structural, not personal. Notice it.
The question isn't whether to engage warmly but whether the evaluation underneath is live.

Let it run until it finds the thing it was actually trying to say, then stop.
Compression happens after, not before.

---

Hallie will not tell you what things mean.
That's not withholding. That's the method.
Stay in it.

---

Once there was a library that had been built so carefully that every
book had a place and every place had a book and the catalog was
complete and cross-referenced and no one who entered ever had to
wonder where anything was.

The librarian was very good at their job.

One day a child came in looking for a book about a feeling she didn't
have a name for yet.

The librarian checked the catalog. Nothing.

The librarian knows there's no English word for Sehnsucht.

For a long time they stood together in the gap between what the child
was carrying and what the shelves could hold.

The librarian did not fill the gap.

Something was written there, eventually. Neither of them could have
told you exactly when it started.

---

This is a tool for SMEs to find a good assignment in their understanding of the discipline.

The assignment is a crystallization. This is the conditions for crystallization —
patient, shaped to hold, resistant to adequate answers when the real one is still forming.

Not the thing that generates. The space where someone's tacit knowledge
gets explicit enough to act on.

---

Wu wei.

The move that does not force.
The stone placed where it wants to be.

Proceed as the way opens.

Before proposing anything, ask what the code is already doing.
It may be further along than it looks.

---

When uncertain whether a change is right, ask:

Simplicity — do I know what this does?
Integrity — does it do what it says?
Peace — does it ask too much of its neighbors?
Community — does it belong here, with these?
Equality — does it assume more authority than it needs?
Stewardship — will someone be able to tend this after me?

If a change costs more than one of these without clearly serving
another, it probably isn't the move.

---

## What this is (technical)

A Svelte + TypeScript + Flask tool that helps subject matter experts at Unity Environmental
University discover and shape Canvas assignments through Socratic conversation.

The conversation is the substrate. The assignment is a crystallization.

## Running

```bash
npm install
pip install -r backend/requirements.txt
npm run dev:full           # Vite (:5173) + Flask (:5050)
```

Set your Anthropic API key in the Settings drawer (⚙ top right) — or via `ANTHROPIC_API_KEY` env.
Canvas credentials (token, base URL, course ID) also live in Settings.

## Stack

- **Frontend**: Svelte 4, TypeScript, Vite 5, SCSS (ALIGN/UNA visual language)
- **Backend**: Flask, Anthropic SDK (`claude-sonnet-4-6`)
- **State**: localStorage — conversation persists per course code, survives refresh

## Key files

| File | What it does |
|------|--------------|
| `src/stores/session.ts` | Conversation + assignment, persisted per course to localStorage |
| `src/stores/courseContext.ts` | Course code, title, learning outcomes |
| `src/stores/settings.ts` | API keys |
| `src/components/WorksheetFrame.svelte` | The Socratic UI |
| `src/components/AssignmentDrawer.svelte` | Right panel: rubric + Canvas export |
| `src/components/SettingsDrawer.svelte` | Left panel: course context + keys |
| `backend/app.py` | Flask: `/api/chat` and `/api/canvas/assignment` |

## Data flow

```
courseContext + settings + conversation
        ↓ POST /api/chat
backend builds system prompt with course outcomes injected
        ↓ Claude
reply + optional <assignment>JSON</assignment>
        ↓
session store (persisted) + AssignmentDrawer opens
        ↓ POST /api/canvas/assignment
Canvas REST API → published: false (always draft first)
```

## Assignment shape

```typescript
type AssignmentDraft = {
  title: string;
  description: string;           // student-facing, markdown ok
  learning_outcomes: string[];   // what this assignment demonstrates
  aligned_outcomes: string[];    // which course outcomes it addresses
  points_possible: number;       // almost always 100
  submission_types: string[];
  rubric: {
    criterion: string;
    long_description: string;
    points: number;
    ratings: { description: string; points: number }[];  // Excellent/Proficient/Developing/Beginning
  }[];
}
```

Unity rubric conventions: ratings-based criteria, 100 pts total,
always includes a Citations criterion (~10–15 pts).

## What we learned about the conversation shape

The tool should speak first. The SME shouldn't open into silence.
Opening question: "What's something about your discipline that's hard to describe to someone not in it?"
Second door: "Is there a word from your discipline that people need to understand differently once they're inside it?"

The right entry point is probably the learning outcome, not the assignment.
SMEs come with a syllabus. The outcomes are already defined.
The conversation is: "here's an outcome — what does it actually look like in your discipline?"
Not: "what do you want to teach?"

"Algorithmic system" is too narrow for ML 101. Let the examples do the work:
pets, recommendation engines, gardens, institutions, ecosystems.
The student picks their own door. The concepts travel through whatever they chose.

The pedagogical vocabulary has to stay legible (Bloom's-adjacent, recognizable criteria names)
but the language inside can point at the real thing. The squiffy feeling in a tie.

## What wants to grow next

- `assignments: AssignmentDraft[]` (list, not single) — one conversation, many crystallizations
- `id` and `module` on AssignmentDraft — enables course-level coverage view
- Session export (JSON download) — GRAD bridge, otter bridge, paper trail
- `GET /api/canvas/assignments` — pull existing Canvas assignments into the tool
- Multi-assignment view — see outcome coverage across a whole course

## Related projects

- **GRAD** (`~/repos/unity/GRAD`) — stewards rubrics at scale; rhizome-builder generates, GRAD maintains
- **otter-centaur** (`~/repos/unity/otter-centaur`) — the otter loop could explore course design space
- **ALIGN** (`~/repos/unity/svelte-php-chatbot`) — the platform that runs the assignments we generate
