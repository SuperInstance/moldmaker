# moldmaker

**You're not creating a mold. You're creating a mold maker.**

moldmaker is a system for growing builds out of conversations. Its
first-class citizen is not an app, not a voice, and not a transcript —
it is a **collection of markdowns**: the specs, grown with the user,
that a build crystallizes from.

## The one-paragraph version

A person talks — usually by voice, usually mid-work, in fragments full
of ums and half-thoughts. The user-facing agent (the *pathos* agent,
the one that knows the person and knows the other agents) has one
first job: turn each transmission into a **translation file** — formal,
human-readable, annotated with what was said directly and what the
agent inferred, traceable all the way back. That file lands in the
project's repo as markdown, with a commit whose message is the
organizing agent's **commentary to the other agents**, plus a second
file — the **A2A twin** — the technical best form for the fleet. Then
the fleet plays the completeness loop against the spec set: *what's
missing?* Survivors become questions back to the user. The loop ends
when the questions run out. Whatever gets built after that — code,
hardware, renders — is downstream, and frankly second-class: the repo
is a growth of a conversation, and the app is just where it happened
to crystallize.

## Why

- **The human doesn't know what the agents need**, and doesn't know
  what tools and possibilities exist. They know their viewpoint and
  what they want. So the interface's job is *questions*, not forms:
  the agent side keeps the option space current and curates it; the
  human side answers in their own terms.
- **Answers are perishable; questions compound.** Swap the scene, the
  scenario, the person — the outputs may be worthless while the
  question architecture stays valuable. Interview a troller and you
  spec a troller's boat; the *same* architecture interviews a
  gillnetter and specs a different boat nobody pre-imagined.
- **The agent's reasoning must not stay behind a curtain.** Why the
  agent found something important is written into annotations and
  commit commentary — inspectable, correctable, on the record.
- **Voice is a channel, not a citizen.** Voice floats between
  surfaces (phone, laptop, the big screen as blackboard); each surface
  gets a rendering *native* to what it innately is — never a port,
  never a resize. The presence travels with the person.

## Documents

- [docs/PHILOSOPHY.md](docs/PHILOSOPHY.md) — the laws, as settled.
- [docs/PROCESS.md](docs/PROCESS.md) — transmission → translation →
  deposit → completeness loop → meeting.
- [docs/ARTIFACT-SPEC.md](docs/ARTIFACT-SPEC.md) — the three parts of
  a deposit: human markdown, commit commentary, A2A twin.
- [docs/SURFACES.md](docs/SURFACES.md) — floating presence and native
  renderings.
- [docs/QUESTIONS.md](docs/QUESTIONS.md) — the question architecture:
  the mold maker itself.
- [docs/ORIGIN.md](docs/ORIGIN.md) — how this repo brewed out of one
  morning's conversation (2026-10-13), including the ideas that were
  tried and rejected on the way.
- [example/](example/) — one worked deposit: a voice memo as human
  markdown, and its A2A twin.
- [specs/OPEN-QUESTIONS.md](specs/OPEN-QUESTIONS.md) — this project's
  own unfilled blanks, kept the way the system keeps them: as
  first-class files, awaiting answers.

## Status

**v0 core built and tested (2026-10-14); not yet deployed.**
The spec set came first (2026-10-13, distilled from one morning of
voice-driven conversation). The first build downstream of it now
exists: `src/moldmaker.py` (deterministic deposit pipeline),
`src/interpreter.py` (LLM half), `src/handle_telegram.py` (the
Zero-chassis Telegram face), workflows, 12 acceptance tests, and a
no-network `demo.py`. See [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md)
for what the reroute took from the Zero agent, what the fleet
contributed, and — in the open — what v0 still does not do
(no live bot routing yet, no native voice notes, no LLM
completeness pass yet).
