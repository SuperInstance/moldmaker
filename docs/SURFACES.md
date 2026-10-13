# Surfaces — voice floats, renderings are native

## The problem this answers

A person walks around their house with work in progress. The house
already contains three abstractions, each innately good at one mode:

- **Laptop** — the granular mode. Sitting, typing, an IDE, big
  scrolling fields of text and files. The working style: skim the
  diffs and headlines, ignore most of it, click into the one file
  you care about, find the tail where the real questions are.
- **Phone** — the next abstraction up. Quick back-and-forth, front-end
  presentation of results. When the user asks how a piece of software
  works, the phone-native answer is a quick deployment page, not code
  explained.
- **TV / big screen** — the best display in the house with the worst
  input, and its own audio. Today it is wasted on entertainment. As
  an engineer's **blackboard** it could hold what no smaller surface
  can: the whole system as a flow chart — the quilt, the pipeline,
  the notes — seen whole, at scale, while talking.

Today, moving between these means starting over: the agent doesn't
come with you, and what passes for cross-surface is an abbreviated
port or a resized cast (PHILOSOPHY IV).

## The design

**Voice is the layer that routes.** Wearing a headset, walking, the
user directs placement by voice: put the flow-chart on the big
screen as the blackboard; bounce this result to the phone to see it
as a newcomer would; keep the granular work on the laptop where it
belongs. Voice doesn't replace a surface — it moves the person and
the work between surfaces.

**The agent is multi-destination, like the human.** Maximum
productivity is not the agent being one thing very well; it's the
agent using all the tools and modalities available to both parties,
and knowing which destination each piece of work belongs on —
including the option of *just talking* when talk is the right
rendering.

**Rendered positionally.** Rendering is listener-relative: the same
work is balanced differently for the person directing (the house
mix) than for the agents working (monitor mixes). Each surface, and
each audience, gets the balance fitted to where they sit.

## What the blackboard is for

The first-class record (PHILOSOPHY II) deserves a first-class place
in the room. The big screen is where the record *lives* visibly: the
outline, the agenda grown from the day's deposits, the system map.
Voice in the ear refers to it — "that flow, second box" — the way a
briefing voice references the outline. Open design questions about
the blackboard live in specs/OPEN-QUESTIONS.md.
