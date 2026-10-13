# Questions — the mold maker itself

## The asymmetry

The human knows their viewpoint and what they want. The human does
**not** know:

- what the agents need in order to act;
- what possibilities exist — the tools, engines, libraries, and
  approaches that appear constantly and might fit this specific job.

So the pathos agent's job is to ask the right questions such that the
**logic agents** and the **hardware agents** receive what they need —
and the huge part of that job is knowing *what to even ask*. The
agent side maintains the other half of the seam: a current survey of
the option space (every new attempt at a 3D game surfaces another
engine that might fit the specific little job better), curated into
real choices the questions can offer — instead of open blanks the
human is expected to fill from knowledge they never claimed to have.

## Calibration

The same question architecture interviews everybody, in their own
register:

- **A kid making a little game** knows nothing of git, CI, or
  pipelines — and must never need to. The questions are fitted so his
  answers, in his own terms, expose what can be automated for him.
- **An engineer eking performance out of a low-level step** gets very
  different options and very different questions: capacity, headroom,
  cost of the step.

Outputs differ wildly; the architecture that produced them is the
same asset. (Rendering fitted per user group, applied to interviews
instead of outputs.)

## The question budget

Questions cost the human attention — the scarcest resource in the
system. So wondering happens in bulk, backstage:

- Hundreds of candidate questions (a Jev running ~250) are generated
  and projected cheaply, without the human present.
- Candidates are filtered by one test — **would the answer change
  the build?** — and sequenced by dependency.
- Only survivors are asked live, inside the dance (PROCESS §5).

A form asks everything it might need. This asks almost nothing — but
the right almost-nothing, chosen from a field of hundreds already
run. And the cascade is legitimate: answered questions license
presumptions in later ones, so the interview accelerates as it goes
— the gillnetter is not asked what the troller already settled for
both of them, only where his answers fork.

## What the output of an answer is

One remaining choice, per answer: does the system need just the
answer, or the answer **plus explanations about the answer**? Both
are legitimate deposits; the specs record which form each answer
took, and explanations are annotations like everything else —
traceable, correctable.

## Growing the repertoire

Questions are kept the way paths are kept: worn by walking
(folders are questions; traversals that produced builds deepen
them). A build that fails at an unfilled blank teaches the sharpest
lesson of all — the missing question gets grafted into the
repertoire, with its scar story attached. The fleet's breeding stock
is its questions; prune nothing without testimony.
