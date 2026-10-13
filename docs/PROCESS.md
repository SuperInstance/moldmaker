# Process — from transmission to meeting

## 1. Transmission

Input arrives the way humans actually produce it mid-life: a voice
memo clicked on a job site, a dictated ramble while walking around
the house, a quick text. Full of ums, half-thoughts, hints of things
("something like that equation, but for…"). No session etiquette is
required of the human. Capture is one tap: **click and go.**

## 2. Interpretation (the first act)

Before any reply, the pathos agent interprets: what is this person
*trying to say*, formally? This is active work with the agent's own
tools:

- a hint of a math equation → construct it, find it exactly;
- a reference that only makes sense with history → inject the context
  from earlier conversations into the intended speech;
- names, places, terms → resolve against the record and the user's
  standing vocabulary.

Output: the **translation file** (see ARTIFACT-SPEC.md). Every element
is annotated: *said* (connects directly to the user's words) or
*inferred* (the agent's construction), with the inference's source
traceable.

## 3. Deposit

The translation lands in the project's repo as one commit carrying
three parts (human markdown, commit commentary, A2A twin — specified
in ARTIFACT-SPEC.md). Filenames carry **no date**; the commit carries
the date. Git supplies ordering and the ledger.

Deposits are fire-and-forget for the human. No reply is owed at
deposit time. The receiving agents work **silently**, as well as they
can — surfacing only hiccups and delivered results.

## 4. The completeness loop ("what's missing?")

The fleet continuously attacks the spec set:

- Jev-style question generation runs in bulk, backstage (hundreds of
  candidate questions are cheap; the human's attention is not).
- Agents ask *what's missing?* — of the specs, of each other, of the
  option space. Most gaps they settle themselves from the record.
- Survivors — gaps only the user can settle — become questions in the
  next live exchange, sequenced by dependency and filtered by one
  test: **would the answer change the build?** Trivia questions die
  unasked.
- The user's answers land in the specs as new deposits, annotated and
  traced like everything else.

The loop converges by **question exhaustion**: when the fleet can no
longer generate a question whose answer would change the build, the
spec is complete *to the limit of the system's ability to imagine* —
which is why question quality is the ceiling (PHILOSOPHY X).

## 5. The meeting

Synchronous, real-time, back-and-forth conversation is the **last
and rarest mode**, and it works because the async layer did the
loading:

- All day, deposits + silent work accumulate. Whatever the agents
  couldn't resolve alone is parked, in order, as an **agenda** — the
  outline, grown rather than written.
- When the human has a real chair and real time, the meeting happens:
  brief voice on top of a prepared outline, senior-engineer style.
- The live exchange itself is a **dance**, not a prompt: call and
  response, both parties iterating on each other. The agent's replies
  exist partly to draw out the next thing the human needs to say.
  Momentum is real and is tuned by knowing the person — shaving off
  the words that don't matter, handing back specs in the right
  directions.

Deposits are the input. The meeting is the withdrawal, prepared.

## 6. Crystallization

When a build is wanted, a coder agent grows it from the spec set —
forward, by diffusion from the specs and questions (PHILOSOPHY VIII),
not backwards from a target image. The build is a rendering of the
specs the way code is a last mile to hardware. If the build teaches
something the specs missed, that becomes a new question grafted into
the repertoire — the mold maker improves.
