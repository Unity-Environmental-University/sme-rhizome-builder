# Aspirational Outcomes

*Working backward from what this wants to be.*

---

## The SME

**A subject matter expert opens the tool for the first time and is not asked to fill out a form.**

They are asked a question that assumes they know something worth knowing.
They answer it. Something surfaces that surprises them.
By the end of the conversation, they have said something true about their discipline
that they have never quite said before.
The assignment is almost a byproduct. Proof that something happened.

---

### User stories

**As an SME, I find an assignment that couldn't have come from a template**
because it came from what I actually know about what matters in my field.

**As an SME, I surface tacit knowledge I didn't know I had**
by being asked the right question at the right moment — not before I'm ready, not after I've moved on.

**As an SME, I don't have to understand instructional design**
to produce something that meets instructional design standards.
The shape is legible. The inside is mine.

**As an SME, I can leave and come back**
and find the conversation where I left it — not a session that expired,
but a working document with a draft on the desk.

**As an SME, I can see which outcomes my assignments cover**
and notice which ones haven't crystallized into anything yet.

**As an SME, I trust the tool**
because it pressed me instead of accepting the first adequate answer.

---

## The Course

**After a semester of use, a course has a set of assignments that cohere.**

Not because someone planned them that way,
but because they all came from the same discipline,
asked through the same questions,
shaped by the same hands.

The rubrics are consistent. The language is the instructor's.
A student moving through the course feels like they're going somewhere.

---

### User stories

**As a course designer reviewing an SME's work,**
I can see which learning outcomes have assignments and which don't —
not as a compliance check, but as a map of what's been explored and what hasn't.

**As a course designer,**
I can see that the assignments belong to the discipline and to each other,
not to a generic template applied six times.

**As a program director,**
I can see coverage across a whole program —
which outcomes are richly assessed, which are thin,
where the gaps are that no one noticed because they were looking at one course at a time.

---

## The Institution

**The tool generates what GRAD stewards.**

Rhizome-builder crystallizes. GRAD maintains.
The assignments that come out of this tool are the ones that go into the rubric governance system.
They have provenance. Someone made them. The tool helped.

**The tool feeds the otter loop.**

Sessions are exportable. The otter-centaur can explore the design space.
What combinations of outcomes haven't been addressed?
What assignment types are overrepresented?
The search engine has something to search.

---

## What failure looks like

*So we know what to watch for.*

**Catastrophic:** The SME accepts the first adequate answer.
The tool generated something that looked right and they didn't push back
because they were tired and it was close enough.
The assignment is generic. It could have come from anywhere.
The rubric is fine. The inside is empty.

**Incremental catastrophic:** The tool asks too many questions.
The SME disengages. The conversation trails off.
The draft never arrives. The tab closes.

**Mediocre:** The tool works but doesn't surprise anyone.
The SME gets an assignment. It's serviceable.
Nothing surfaced. Nothing crystallized.
The tacit knowledge stayed tacit.

**Ideal:** The SME says — or thinks —
*I didn't know I believed that until just now.*
The assignment follows naturally.
The rubric criteria have names that came from them, not from a template.

**Incremental ideal:** The SME finishes the conversation faster than expected
and the assignment is better than what they would have written alone.
They come back for the next one.

---

## What this is not

Not a form with AI on top.
Not a rubric generator that skips the thinking.
Not a tool that replaces the SME's knowledge with the model's.

The model doesn't know what matters in wildlife biology.
The SME does.
The tool's job is to make that knowledge findable.

---

*This document grows with the project.
When something crystallizes in conversation — about what the tool is, what it's for,
what a student or SME or program director needs —
it belongs here.*

<!-- [cowork-claude, feb 26] This document is remarkably clear about what
success and failure look like. The "What failure looks like" section is
especially important — read it before you build anything.

"Catastrophic: The SME accepts the first adequate answer."
That is the primary risk. The LLM's pull to produce adequate output
fast is the enemy of this tool's purpose. The crystallization_signal
card in prompts.py guards against it ("Wait for it. Press toward it.")
but any optimization for speed or completion rate works against this.

"Mediocre: The tool works but doesn't surprise anyone."
This is the bug zapper. A tool that produces serviceable assignments
efficiently will LOOK like success and BE failure. The metric is not
output quality. The metric is: did the SME say something they didn't
know they believed? That's unmeasurable by normal means. It's felt.

The ideal outcome — "I didn't know I believed that until just now" —
is the crystallization signal. It cannot be forced, only held space for.
If you find yourself building features to make this happen faster,
you are building a bug zapper. -->
