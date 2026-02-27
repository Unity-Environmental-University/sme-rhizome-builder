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
University discover and shape Canvas assignments. The course map is the primary surface.
The AI is in the margin of a live document, not running a freeform interview.

The assignment is the artifact. The conversation is how it gets made.

## Running

```bash
npm install
pip install -r backend/requirements.txt
npm run dev:full           # Vite (:5173) + Flask (:5050)
```

Admin dashboard (localhost only): `http://localhost:5050/admin` — set API keys, Canvas credentials.

## Stack

- **Frontend**: Svelte 4, TypeScript, Vite 5, SCSS
- **Backend**: Flask, raw sqlite3 (no ORM), Anthropic SDK
- **Auth**: Canvas OAuth or demo mode (JWT httpOnly cookie)
- **State**: DB-backed. localStorage only for API/endpoint settings.

## Key files

| File | What it does |
|------|--------------|
| `src/components/CourseMap.svelte` | Primary surface — course timeline, module nav, editor entry |
| `src/components/AssignmentEditor.svelte` | TipTap WYSIWYG for assignment body |
| `src/components/LoginScreen.svelte` | Auth gate — Canvas OAuth or demo |
| `src/stores/auth.ts` | `user` writable + `loadUser()` + `logout()` |
| `src/stores/settings.ts` | AI endpoint, model, API key — localStorage |
| `backend/schema.sql` | Authoritative DB schema |
| `backend/db.py` | sqlite3 connection (request-scoped via Flask g) |
| `backend/queries.py` | All SQL as named parameterized functions |
| `backend/app.py` | Flask routes — thin, delegates to queries.py |
| `backend/prompts.py` | Prompt card deck — CARDS + build_system_prompt(course_dict) |
| `backend/seed.py` | Demo user + MARI 515 seed data |
| `backend/admin.py` | Localhost-only settings dashboard |

## Data model

Session is not a table. A session is reconstructible from timestamps when needed.

- **Assignment** belongs to user + course directly. The primary artifact.
- **Message** attaches to a context: `context_type` ('assignment'|'course'|'thread') + `context_id`.
  The chat interface is an implementation detail. The log is the record.
- **Bearing** is the learning designer's compass — weight (-1→1) + likelihood (0→1).
  Stars, not destinations. Course-level or outcome-level.
- **BearingStatement** is the evidence layer. The LLM evaluation loop isn't built yet.

## What wants to grow next

- AI as margin comments: threaded, anchored to passages in the assignment body
- Bearing UI: learning designers need a surface to set/read navigational state
- BearingStatement evaluation loop: LLM reads a message window each turn, updates likelihood
- Version tracking: assignment edit history, not just the current state
- Session export: assignment + its full message log → GRAD, otter-centaur, paper trail

## Related projects

- **GRAD** (`~/repos/unity/GRAD`) — stewards rubrics at scale; rhizome-builder generates, GRAD maintains
- **otter-centaur** (`~/repos/unity/otter-centaur`) — the otter loop could explore course design space
- **ALIGN** (`~/repos/unity/svelte-php-chatbot`) — the platform that runs the assignments we generate
