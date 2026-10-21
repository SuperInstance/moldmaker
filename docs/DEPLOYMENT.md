# Deployment — the live route, the evidence, and what's still broken

Status as of 2026-10-21: **deployed and live-verified.** This page is
the readable record of how Moldmaker went live, what proves it, and —
first-class, per house rules — what is still wrong.

## The live route

```
Telegram (the existing lobster bot)
  -> lobster-telegram-bridge (Cloudflare Worker)
       messages beginning "mold:" or "/mold " are stripped of the
       address and dispatched ONLY to this repo; every other message
       keeps the original lobster route, unchanged
  -> .github/workflows/moldmaker-telegram.yml (repository_dispatch)
  -> src/handle_telegram.py -> src/interpreter.py (vault -> MiniMax)
  -> src/moldmaker.py (validate, file, commit)
  -> the dogfood/ store in this repo (one commit per deposit)
  -> acknowledgement back through the bridge
```

The vault (`superinstance-vault` Worker) carries this repo on its
allowlist and brokers the LLM call; the workflow authenticates to it
with a GitHub OIDC token. No secrets live in this repo.

**To use it:** send the existing Telegram bot a message beginning
`mold:` followed by the memo. Dictated text works today (Telegram
sends it as text). Native voice notes do not — see deficits below.

## The evidence

- First fully green live run:
  [run 38703835143](https://github.com/SuperInstance/moldmaker/actions/runs/38703835143)
  — every step green, including *Deposit the transmission* and
  *Reply via bridge*.
- First live deposit, commit `2d59f36` ("deposit: Boat Launch
  Checklist App Request"), in the `dogfood/` store:
  - human file: [boat-launch-checklist-app-request-91e6b4ef.md](../dogfood/deposits/boat-launch-checklist-app-request-91e6b4ef.md)
  - A2A twin: [boat-launch-checklist-app-request-91e6b4ef.a2a.json](../dogfood/deposits/boat-launch-checklist-app-request-91e6b4ef.a2a.json)
  - generated views: [INDEX](../dogfood/specs/INDEX.md) ·
    [ACTIONS](../dogfood/specs/ACTIONS.md) ·
    [OPEN-QUESTIONS](../dogfood/specs/OPEN-QUESTIONS.md) ·
    [AGENDA](../dogfood/specs/AGENDA.md)
- The interpretation behaved the way the spec demands: the memo's
  unresolved *"whoever usually checks the fuel dock"* was **not**
  invented into a name — it became the open question
  `identify.fuel.dock.checker`. Both actions are `proposed`; nothing
  was auto-approved.

## The fault stack (what it took to get one green run)

Six faults, peeled in order, each fixed at its own layer with a
regression test. Successes are the baseline; this list is the report.

| # | Symptom | Root cause | Fix |
|---|---------|------------|-----|
| 1 | Run "succeeded", nothing filed | Deposit commit had no git identity in the fresh CI checkout; the workflow masked the failure with `|| true` | `ensure_identity()` in the pipeline; the workflow now fails red unless the handler result is `ok` (`11adfb4`) |
| 2 | `unknown url type: '/proxy'` | The unset `VAULT_URL` repo variable expanded to `""`, overriding the code default | Empty env falls back to the default vault URL (`5815810`) |
| 3 | HTTP 403 from the vault | Cloudflare's edge blocks Python-urllib's default user agent (error 1010 — looks exactly like an auth 403) | Identify with a `moldmaker/0.1` user agent; HTTP error bodies are surfaced so a real rejection names itself (`b0c044a`) |
| 4 | `bad owner 'software-agent'` | MiniMax invented an action-owner label outside the schema, on every retry | Owner vocabulary is a routing hint, not provenance: obvious synonyms normalize to the canonical owner (software → `logic-agent`), unknowns coerce to `unspecified`, and every change is recorded in `validation_notes` (`d119ea7`) |
| 5 | `uncommitted changes outside the store (['dogfood/'])` | In a fresh checkout the store is a brand-new subdirectory; git collapses an untracked directory to one `dogfood/` entry, which matches none of the dirty-tree guard's allowed file prefixes — the guard fired on the store's own newborn files | The guard lists untracked files individually (`--untracked-files=all`); a genuinely foreign file still blocks (`dcf1e54`) |
| 6 | Retry of an already-filed message failed | The pipeline re-interpreted and validated a fresh LLM reading *before* checking whether the message was already filed — a retry was exactly as fragile as a first attempt | The deposit id never depends on the interpretation, so the already-filed check now comes first in `deposit()`; the Telegram handler short-circuits a known `message_id` before any LLM call (`037a4c1`) |

Test suite: **34 tests**, all passing as of 2026-10-21
(`python3 -m unittest discover -s tests`), including the cold
audit and think question-memory tests added with the referee
pass. Each fault above has a regression test that reproduces
the live failure on the old code.

## What is still broken or missing (2026-10-21)

- **Fault 6 — live re-verification VERIFIED 2026-10-21.** The
  earlier GitHub rate limit (a direct dispatch returned
  `403 API rate limit exceeded` at 16:38 UTC on 2026-10-21) had
  cleared by the evening run. Re-sending the already-filed
  message 99006 through the bridge produced run
  [39681461783](https://github.com/SuperInstance/moldmaker/actions/runs/39681461783)
  — conclusion `success`, *Deposit the transmission* green,
  *Reply via bridge* green, and `origin/main` unchanged by the
  run (`4b72880` before and after): no duplicate deposit, no
  fresh LLM interpretation. Fault 6 is closed end-to-end.
- **No native voice notes.** The bridge forwards text only. Voice
  needs: bridge accepts `message.voice` → fetch audio → retain
  audio + reference → STT → payload with transcript + `audio_ref`.
- **The think cycle's LLM pass still awaits a successful live
  run.** First live attempt 2026-10-21: run
  [39681607533](https://github.com/SuperInstance/moldmaker/actions/runs/39681607533)
  failed in the *LLM completeness pass* step with
  `RuntimeError: HTTP 401 from https://superinstance-vault.casey-digennaro.workers.dev/proxy: {"error":"OIDC verification failed"}`.
  No `think:` commit landed and no `dogfood/specs/THINK.md` was
  produced. The completeness pass (`src/think.py`) remains built
  and unit-tested offline; this vault OIDC failure is the open
  blocker for its first live run.
- **Minimal routing.** Chat→project mapping is an env JSON; there
  is no project-selection conversation yet.
- **No surfaces beyond Telegram + git.** Phone/laptop/TV native
  renderings (docs/SURFACES.md) are still design.
- **Interpretation quality is the frontier.** Validation guarantees
  traceability, not wisdom.

## Where the rest of the story lives

- [docs/IMPLEMENTATION.md](IMPLEMENTATION.md) — the build, the
  Zero reroute, and what the fleet contributed (taken and refused).
- The `dogfood/` store itself — the system eating its own cooking:
  deposits, generated views, and a git log whose commit messages
  are the commentary.
- The design set: [PHILOSOPHY](PHILOSOPHY.md) ·
  [PROCESS](PROCESS.md) · [ARTIFACT-SPEC](ARTIFACT-SPEC.md) ·
  [SURFACES](SURFACES.md) · [QUESTIONS](QUESTIONS.md) ·
  [ORIGIN](ORIGIN.md).
