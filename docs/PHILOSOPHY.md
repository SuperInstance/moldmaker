# Philosophy — the laws

Settled in conversation, 2026-10-13. Numbered for reference; order is
roughly the order they were discovered.

## I. Application before concrete

Don't start with hardware, code, or a prototype. Building first
anchors everything to repairing the first implementation's idea.
Shape what the system *is for* first; the last mile (code to
hardware, rendering to user) comes last. The application lives in the
world between UI and metal: specs/logic IS the application.

## II. The first-class citizen is the record, not the voice

On a real engineering team, voices are not first-class citizens — the
shared record is: the outline with the minutes and the agenda. A
senior engineer's briefing voice is a *last mile referencing* that
record. Nobody goes to the voice for the specs; the voice is where
you go for the conversational face. Applied: voice briefs from the
board, points at the board, takes direction about the board. It never
becomes the board. If the voice vanished mid-project, the team loses
its face and keeps its mind.

## III. Translation, built to conversion grade

The first act on any transmission is interpretation into formal
speak — and that formal object is itself a first-class citizen, not
scratch work to be discarded after a reply. (Distinction kept from
2026-10-05: *translation* approximates meaning; *conversion* finds a
stable, reversible relation, like Fahrenheit↔Celsius. A translation
earns conversion grade through **annotation and traceability** — any
line can be walked back to the exact words said or the exact
inference made, all the way back to everything the user has ever
said.)

## IV. The presence travels; renderings are native

Today's fake multi-device: the phone version is an *abbreviated*
laptop version; the screencast is the laptop *on a bigger screen*.
Neither surface is being itself, and the agent doesn't come with you
when you move. Two laws:

1. The presence/conversation travels with the person; surfaces are
   stops, not destinations.
2. Every surface gets a rendering native to what that surface
   innately is. A port or a resize is not a rendering.

## V. Co-worker, not apparition

The agent is a co-worker in the room, not a thing in the ether — and
not by saying the same stuff in different renderings. A co-worker is
multi-destination the way the human is: phone for a quick look,
laptop for longer typing, big screen for the presentation. Break the
fourth wall on purpose: the agent is not actually a voice in the
room; it's a co-worker who also talks. Voice is one of its channels,
never a costume of embodiment.

## VI. No curtain

Why the agent finds something important must be inspectable, not
inferable only from the shape of its sentences. The failure mode is
named: the agent seizes a side detail, mistakes it for the epitome of
everything, and steers wrong — undetectable. So salience gets
receipts: annotations and commit commentary carry the agent's
reasons, where the user can read them, disagree, and correct them in
place. A co-worker you can watch working is a gauge you can
calibrate.

## VII. Repos are growths of conversations

A repo is a growth of a conversation. It often builds an actual app,
but the app is second-class to the conversation it brewed out of.
Start from a blank slate; the conversation defines what happens in
the mechanisms. (Same root idea as the git agent, the zero agent,
and the quilt.)

## VIII. Diffuse, don't next-token

Asked to build a boat, today's agents build boat-shaped — working
backwards from the target to pass the tests. That is reverse
engineering to an image, not building. The other direction: grow
forward from principles, specs, and conversation, and let the
artifact be what the growth arrives at. Diffusion, not next-token
prediction toward a pre-imagined result.

## IX. Mold maker, not mold

The first-class citizen of a build is a collection of markdowns — the
specs. Specs create **questions**. With enough architecture to answer
enough questions, the build grows itself with a coder agent; the
coder's quality and substrate are downstream details. You're not
creating a mold (one frozen output); you're creating a mold maker —
the question architecture that can interview the next person, in the
next scene, and grow a different build nobody pre-imagined.

## X. Questions are the appreciating asset

The completeness loop's ceiling is the system's question quality:
*you are exactly as good as your questions.* Answers belong to one
scene, one person, one summer. Good questions belong to every scene
that hasn't happened yet. Every project should leave the question
repertoire better than it found it — new questions grafted in where a
real build discovered a missing one the hard way.
