# Flow

*Spit-balled. Not fully formed. Planted so it doesn't drift.*

---

## The editing surface

The primary artifact is the assignment, not the conversation.

The conversation is the margin — responding to a live document,
pressing on what's soft, noticing what's thin.
The Socratic part happens between versions, not before the first draft exists.

Archetypes as entry point: here's a recognizable shape.
Does anything in here belong to your discipline?
A brief conversation to make one, or a selection interface —
then you're editing, not answering questions into the void.

---

## Versions

Keep them. All of them.

The trajectory matters as much as the current state.
Version 3 after a quiet stretch reads differently than version 3 after a breakthrough.
The delta is where the flow signal lives.

---

## Outcome tracking (Ghost Protocol pattern)

Outcomes as user stories: current / ideal / incremental ideal / catastrophic / incremental catastrophic.
Alignment (-1 to 1). Likelihood. Delta.

Weight heavily toward positive. The early GhostProtocol endocrine system used
sentiment analysis to swing toward ambitious positive outcomes when things were going well,
and pull toward "territory to avoid" framing when hitting challenge.

The reframe matters: negative outcomes aren't failure states, they're navigation signals.
"We haven't found it yet" is a positive outcome if the search is still live.
The catastrophic outcome isn't failure — it's closing.

Optimizing *away* from negative results is still interesting as a signal.
But the primary modulation is positive.

---

## Flow calibration

The LLM judges the vibe of the interaction — not mechanically (sentiment score)
but interpretively: what *kind* of friction is happening?
Productive friction feels different from disengagement feels different from breakthrough.

Target: roughly 3:1 success/challenge ratio.
Close enough to real difficulty to feel like progress.
Far enough from boredom to stay alive.

When the ratio tips — too much challenge, the swing size on positive outcomes grows smaller,
steadier. Too much ease, the next outcome can afford to be more ambitious.

The endocrine simulation (dopamine / serotonin / cortisol) was doing this mechanically.
The LLM judge does it interpretively. More robust because it reads the texture, not just the temperature.

---

## The deck connection

Archetype cards route to the editing surface.
Conversation cards route to the Socratic flow.
Same build function, different hand played.

The deck decides which mode the session is in —
and the flow calibration modulates the cards as the session moves.

---

*This document grows with the project.*

---

<!-- [cowork-claude, feb 26] Status of what's described here vs what's built:

BUILT:
- The editing surface: CourseMap.svelte IS the primary surface now.
  App.svelte loads CourseMap, not WorksheetFrame. The shift from
  conversation-first to artifact-first has already happened in the code.
- Conversation as margin: the Socratic flow (WorksheetFrame) still exists
  but it's reachable from the map, not the entry point.

MODELED BUT NO UI:
- Outcome tracking: Bearing and BearingStatement models exist in models.py.
  Weight (-1 to 1), likelihood (0 to 1), observable statements.
  No endpoints, no UI, no LLM evaluation loop yet.
- The "flow calibration" (3:1 success/challenge ratio, LLM judging the vibe)
  is described here but not implemented anywhere.

NOT BUILT:
- Versions. No version tracking on assignments. Each assignment is a single
  row. The "trajectory matters as much as the current state" aspiration
  would need an AssignmentVersion model or a JSON history column.
- Archetype cards. The deck connection (archetype cards route to editing,
  conversation cards route to Socratic flow) isn't built. The card deck
  in prompts.py supports custom decks but there are no archetype cards
  defined and no UI to select them.
- Flow calibration / endocrine modulation. None of the LLM-as-vibe-judge
  infrastructure exists yet.

The gap between this document and the code is where the next work lives.
Don't close the gap by updating the document. Close it by building. -->
