# Questions for Hallie

Things I read carefully and genuinely don't know the answer to.
Answering these helps me help you without filling in the gap with a guess.

---

## 1. Course description is always empty
`CourseMap.svelte:54` — `description: ''`

`CourseShape` has a `description` field. `CourseOverview` renders a "Description" section.
But the schema has no description column, and CourseMap hardcodes it to empty string.

Is this:
- A placeholder for a field that's coming?
- A section of CourseOverview that shouldn't exist yet?
- Something you want to pull from Canvas when the course is imported?

---

## 2. `module_label` as the join key
`CourseMap.svelte:73` — `a.module_label === \`${pt} ${m.position + 1}\``

Assignments link to modules by a string label ("Week 3", "Unit 4") rather than by `module_id`.
Modules are now real DB records with IDs. `models.py` says the reconciliation needs to happen —
`assignment.module_id` FK to `modules.id`. The string match works but it's fragile.

Is there a reason to leave it as a string label for now?
(One reason I can think of: it lets you create an assignment before the module exists.
Another: it's simpler to reason about in the editor. Is either of those the reason?)

---

## 3. ~~Where does the conversation happen?~~ — Settled (2026-03-04)

The freeform chat model is gone. No single accumulating conversation context.

Instead: **Google Docs-style anchored interactions.** Notes attached to specific passages
in the assignment. Threaded replies. Not one chat — many discrete anchored exchanges.

**Two agents:**
- **Context concierge** — reads course, outcomes, bearings, log history. Builds orientation.
  Hands context (not orders) to the communication agent. *If the concierge acts, it logs.*
- **Communication agent** — writes the notes the SME sees. Responds to selections/replies.
  Acts from the concierge's context, not from a blank prompt.

Log shape: concierge logs its read (minimal to start, structured later), communication agent
logs the note it writes. Both in the same context, linked by `replied_to` or proximity.

The `/api/chat` endpoint and its accumulated message history can go. The log_entries
structure (`replied_to`, `context_type + context_id`) already fits this model well.

**Trigger — settled:**
- **Auto**: fires on save when description has non-trivial content (threshold TBD, ~50 non-whitespace chars to start)
- **Manual**: "unstuck" button — SME explicitly invites the agent in, even to thin content

Concierge logs which mode fired. Communication agent's posture differs:
- Auto: observational — reads what's there, responds to it
- Unstuck: generative — SME is stuck, agent can push, ask, open space

**Open:** exact threshold for "non-template content"

---

## Notes UI — settled (2026-03-04)

**Sidebar, not bottom.**

Bottom-appended notes become a scroll — gravity takes over, you're managing a feed
instead of a document. The sidebar stays spatially stable as the document grows.

Shape:
- Three-column layout when editor is open: nav | editor | sidebar
- Sidebar is collapsible (hidden when SME just wants to write)
- Highlights in the document body anchor to threads in the sidebar
- Agent highlights a span, leaves a note anchored to it
- SME clicks a highlight → sidebar opens to that thread
- Sidebar positioned beside the highlight, not below everything

**Settled:** passage-level from the start. Load-bearing — building without it means
rebuilding the interaction model later, not adding a feature.

**TipTap mark** carries: `comment-id` (UUID matching a log thread root entry).
**Log thread**: root entry is `action_type='agent_note'` or `'sme_anchor'`, with
`content` = JSON `{span_text, comment_id, mode}`. Replies chain via `replied_to`.

**Three entry points, same structure:**
- Agent on save: reads draft, picks a passage, highlights it, notes anchored there
- SME selects text + unstuck: "this part" — agent responds to that span specifically
- SME replies to an existing highlight: thread continues in place

The highlight IS the conversation location. Every thread has a home in the document.

**Unstuck is selection-aware:**
- With selection: agent responds to that passage specifically
- Without selection: agent reads the whole draft

**Designer surface — settled (2026-03-04)**

Designer mode in CourseNav — a ⚙ link at the bottom of the nav.
Opens a DesignerView (third view alongside 'course' and 'module').
Same auth, same app. No separate role needed for v1.
Bearings list + add form. Weight slider. Likelihood read.

---

## 4. The `draft` badge is hardcoded
`ModuleView.svelte:183` — `<span class="module-view__draft">draft</span>`

Every assignment in the list shows "draft" regardless of its actual snapshot label.
Snapshot labels in the schema: `null`, `draft`, `manual`, `crystallized`, `canvas_push`.

Is "draft always" intentional while Canvas integration isn't live?
Or should the badge already reflect actual status?

---

## 5. One course per user
`CourseMap.svelte:44` — `const c = courses[0]`

There's no course-selection UI. For the prototype this is fine.
But: a real SME at Unity might be teaching two or three courses this semester.

Is the one-course assumption intentional until something specific changes?
What would trigger adding a course picker — Canvas import? A separate course list view?

---

## 6. Who sets Bearings, and when?
`bearings.py` — full CRUD API, no frontend

Bearings are injected into the system prompt silently (the SME doesn't know they're there).
The schema and API are complete. The learning designer sets them; the SME doesn't need to see them.

Does the learning designer need a separate authenticated role, or just a separate view within the same app?
Is there a timeline for this — is it next after the chat surface, or is it further out?

---

## 7. ~~Both sides of the conversation are `ai_turn`~~ — Moot (2026-03-04)

The `/api/chat` endpoint and its message history model are going away.
The new interaction model is anchored notes, not a chat thread.
`action_type` for the new agents will be something like `'context_read'` (concierge)
and `'agent_note'` (communication agent). To be decided when built.

---

## 8. ~~What happens after crystallization?~~ — Settled (2026-03-04)

Drafts come to exist because a person (SME or learning designer) creates one.
Human intent, not AI output. Click "add assignment," give it a title, start writing.

The crystallization-via-chat path is off the table:
- `_extract_assignment()` in `app.py` — dead weight
- `<assignment>` tags in `output_format` card — dead weight
- `crystallization_signal` card in `prompts.py` — dead weight

The assignment identity + snapshot model is still right.
The AI's job is to be in the margin of a draft that already exists.

---

*These are live questions, not suggestions. Don't feel obligated to answer all of them now —
even a partial answer helps me know what to build toward and what to leave alone.*
