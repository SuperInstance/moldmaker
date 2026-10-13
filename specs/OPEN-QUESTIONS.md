# Open questions — this project's unfilled blanks

Kept the way the system keeps them: as questions, each marked with
*why the answer would change the build* (the only admission test,
docs/QUESTIONS.md) and where it currently sits. Answered questions
move out of this file into the specs they settle, with the deposit
that answered them linked.

## About the blackboard

1. **Persistent, summoned, or both?** Is the big-screen blackboard an
   ambient always-on view, a view summoned per piece of work, or an
   ambient view whose focus is summoned? — *Changes the build:*
   determines whether the TV rendering is a living dashboard agent
   or a presentation renderer.
2. **What earns the big screen?** What rule promotes a piece of work
   to the blackboard vs keeping it on phone/laptop? Candidates:
   whole-system views only; anything the user is currently
   *directing* rather than *editing*. — *Changes the build:* the
   routing layer's core policy lives here.
3. **Private channel vs room channel.** Does spoken output ever come
   from a surface's speakers, or is voice always in the headset?
   — *Changes the build:* multi-person rooms, guests, and the
   party-line question all fork on this.

## About deposits

4. **Where does annotation live in the file?** Inline margin lines
   (as in example/) interleave said and meant in one read; a parallel
   annotation file keeps Layer A pristine but splits the read.
   — *Changes the build:* every downstream reader implements this.
5. **Green-light threshold.** Which interpretations are
   "consequential" enough to wait for approval before hardening into
   the A2A entrance? Working proposal: anything that spends money,
   speaks to another person, or deletes — plus anything the agent
   itself flags low-confidence. — *Changes the build:* this is the
   trust dial for the whole fleet.
6. **Audio retention.** Layer A says "as close to exact as can be
   got" — is the audio itself kept forever, kept until the transcript
   is verified, or kept per-project by policy? — *Changes the build:*
   storage, privacy posture, and the witness chain's strength.

## About the loop

7. **Who may graft questions?** When a build fails at an unfilled
   blank, the missing question is grafted into the repertoire. May
   any agent graft, or does grafting require the pathos agent (who
   owns the interview) — or the user? — *Changes the build:* the
   repertoire is the appreciating asset; its write-permissions are
   governance.
8. **Question exhaustion across projects.** Does the completeness
   loop run per project only, or may a question sharpened in one
   project be *offered* to another project's interview? —
   *Changes the build:* cross-project transfer is where the mold
   maker starts to feel like a platform rather than a habit.
9. **The kid test.** The calibration law says the interview must fit
   a kid who knows no git. What is the *minimum viable deposit* from
   a user who can only answer questions — no memos, no rambles?
   — *Changes the build:* defines the floor of the whole interface.

## About this repo itself

10. **Name.** "moldmaker" is the founding metaphor's name, chosen
    from the conversation's closing line. Names here are handles,
    not commitments; if the system grows a better one, this file is
    where the rename gets proposed and settled.
