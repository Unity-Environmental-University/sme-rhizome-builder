"""
Domain design notes — SME Rhizome Builder.

The schema lives in schema.sql.
The queries live in queries.py.
This file is where the design questions live.

────────────────────────────────────────────────────────────────────────────────

# On the shape of data

The shear between storage and domain was real. SQLAlchemy flattened the data into
one shape but the data serves multiple masters: Canvas API, the editor surface,
the course map, eventually GRAD and otter-centaur. Each consumer wants a different
shape. The ORM was solving a different era's problems.

Raw sqlite3 + named query functions + plain dicts: the shape of data is now explicit
at every callsite. You can read what a query returns. You can read what a route sends.
No magic.

────────────────────────────────────────────────────────────────────────────────

# On Session

Session is not a table.

A session is reconstructible from (user_id, context_type, context_id, created_at)
when you need the concept. The artifact and its log are the primary records.

The old Session table was a container that existed because the chatbot needed a thread.
In the course-map-first design, the artifact is primary. The conversation is in the margin.

If you ever need "what happened in one sitting": query messages WHERE context = X
AND created_at BETWEEN start AND end. The session emerges from the log.

────────────────────────────────────────────────────────────────────────────────

# On Message

Messages attach to a context — not a session.

context_type: 'assignment' | 'course' | 'thread'
context_id:   the id of that thing

This is an open-ended list, not a closed enum. A string tag is honest
about what it actually is. If a new context type makes sense, add it.
The index on (context_type, context_id, position) makes it fast.

The question "is it a chat or a log or a memory?" resolves like this:
- While the session is live: it reads like a chat
- After the session: it is a log attached to an artifact
- Across multiple sessions: it wants to be a memory, but the curator problem
  isn't solved yet. Who decides what gets remembered? If the LLM decides,
  selection bias enters the Bearing system.

For now: it's a log that wears a chat's face. The flat list is adequate.
The recursive context tree (messages with causal relationships, prunable without
losing structure) is the right eventual shape. Build the Bearing evaluator to
receive a window of messages, not the full history, so it survives that refactor.

────────────────────────────────────────────────────────────────────────────────

# On Assignment

Assignment belongs directly to user + course. No session intermediary.

It serves Canvas (push/pull), the editor surface, the course map, and eventually
GRAD. Each consumer gets a different view via _assignment_dict() in app.py.
The rubric JSON column is where the most pain will accumulate — it's untyped
and GRAD will want to validate its structure. TypedDicts as view types in Python
(or proper TypeScript types on the frontend) are the right move when that pressure
arrives. Don't add them prematurely.

The "shared" boolean moved here from Session. A shareable assignment with its full
message log is the unit of provenance — the thing that goes to GRAD, to otter-centaur,
that has a paper trail.

────────────────────────────────────────────────────────────────────────────────

# On Bearing

Bearing is the GhostProtocol endocrine system translated into course design.
Stars, not destinations (see the epistemic notice in otter-centaur/LICENSE).

weight:     -1 to 1 (sail toward / sail away from)
likelihood: 0 to 1 (current read on whether we're there)
delta:      weight - likelihood (the signal; not stored, computed on read)

High weight + low likelihood = push harder.
Low weight + high likelihood = maybe this isn't the interesting direction anymore.

Bearings are course-level or outcome-level. The old session-level bearing
(emergent from a specific conversation) is now an assignment-context message pattern,
not a separate bearing type. If a bearing crystallizes from a conversation,
attach it to the course.

The LLM evaluation loop (evaluating BearingStatements each turn) isn't built yet.
When it is: be careful about the LLM's pull to affirm. The system should be as
willing to disconfirm a Bearing as to confirm one. The evaluator should receive
a window of messages (not the full log) and return {statement_id, observed: bool}.

────────────────────────────────────────────────────────────────────────────────

# What's still live (don't resolve without conversation)

- The rubric JSON column and GRAD's validation requirements. TypedDicts? Pydantic?
  Not yet. Wait until GRAD actually starts reading this data.

- Versions. No version tracking on assignments. The "trajectory matters as much as
  the current state" aspiration (flow.md) would need an assignment_versions table
  or a JSON history column. The message log is a partial substitute — you can see
  what was said before each edit. But it's not the same as diffing the assignment itself.

- The Bearing evaluation loop. When you build it, the architecture question is:
  does it run synchronously per chat turn (slow, blocks response) or as a background
  job after the turn completes? Background is better but needs a job queue.
"""
