# Example deposit

One worked deposit, end to end, in the format specified by
[docs/ARTIFACT-SPEC.md](../docs/ARTIFACT-SPEC.md):

- `voice-memo-boat.md` — the human markdown: Layer A (the said) with
  Layer B annotation lines running through it, marked `> ▸`.
- `voice-memo-boat.a2a.json` — the A2A twin: the same deposit as
  structured intent for agents, every element traced to a section of
  the human file.

The third part of the deposit — the commit commentary — is not a
file. It is the message of the git commit that lands these two files.
Read it with `git log`. That is deliberate: this repo dogfoods its
own spec.
