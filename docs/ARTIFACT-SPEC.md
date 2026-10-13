# Artifact spec — one deposit, three parts

Every transmission — a voice memo, a dictated ramble, a text like the
ones in any working chat — is stored in the project's (private) repo.
One deposit = one commit = three parts.

## Part 1 — The human markdown

The user's speech, kept human. Two layers inside one file, never
blurred:

**Layer A — the said.** As close to an exact rendering of what was
said as can be got, straight from the audio (audio retained where
the deposit began as audio). Cleanup is *structural only*:

- find the topic sentences and headings; break into sections;
- tidy grammar **for clarity only** — no other intention may ride
  along in a wording change. The agent does not improve, complete,
  or silently correct what the user said in this layer.

**Layer B — the meant.** Annotation lines running throughout the
markdown, the way comments run through code — little descriptions of
what each passage means *for the project*: the action hiding in a
sentence, the equation the user hinted at (built, exact), the context
injected from an earlier conversation (linked), the inference and
its confidence. Annotations are visually and structurally distinct
from the user's words. They never rewrite Layer A.

So any reader — the user tomorrow, another person, another agent —
can see exactly what was said AND what the user-facing agent made of
it, and precisely where the two diverge. The divergence is visible,
not smoothed over. That visibility is the trust mechanism.

## Part 2 — The commit commentary

The commit that lands the deposit carries a message written by the
organizing agent **facing the other agents**. Not bookkeeping —
briefing:

- the tone of the transmission;
- what this means, in the agent's judgment — including *why it found
  things important* (PHILOSOPHY VI: no curtain);
- connections to other things: other deposits, other projects,
  standing decisions, open questions this touches.

A fresh agent arriving at the project reads the commentary chain
first to get its bearings (orientation), then reads the record.

## Part 3 — The A2A twin

A second file: truly the agent-to-agent version — the technical best
presentation of the same material for the rest of the agents
(structured intent, resolved references, extracted actions, links to
sources). Not usually for the human, and doesn't pretend to be.

**Provenance test:** a senior engineer must be able to set the human
markdown and the twin side by side and see how the one came from the
other. Every element of the twin traces to spans of the human file,
and through its annotations to the audio and the record.

## Rules that bind all three parts

- **No date in filenames.** The commit carries the date; git is the
  ledger.
- **Corrections are new entries**, never edits-over: if the user
  corrects an interpretation, the correction is deposited and traced;
  the original annotation stays readable. (The ledger teaches the
  crashes too.)
- **Consequential interpretations wait for a green light** before
  they harden into the A2A entrance point. Routine ones proceed under
  the agent's standing authority.
- **Private by location, not by obscurity**: deposits live in the
  project's private repo. Secrets never enter deposits at all.
