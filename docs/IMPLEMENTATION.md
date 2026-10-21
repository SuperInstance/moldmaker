# Implementation — v0, and how it reroutes Zero

Status as of 2026-10-21: **built, deployed, and live-verified**
(first live deposit 2026-10-15; the deployment record — route,
evidence, fault stack, current deficits — lives in
[DEPLOYMENT.md](DEPLOYMENT.md)). This document is the honest map:
what exists, what it was built from, what the fleet contributed,
and what is still missing.

## The reroute, in one picture

Zero (SuperInstance/zero-poc) already had the body: a Telegram bridge
firing `repository_dispatch`, a vault for LLM access, GitHub Actions
for a heartbeat, repo files + git log as memory, and a ReAct loop for
hands. Its Telegram flow was *hear text → brief reply*.

Moldmaker keeps the body and replaces the middle:

```
Telegram payload
  -> src/handle_telegram.py   (thin face: routing, acknowledgement)
  -> src/interpreter.py       (LLM half: transmission -> interpretation JSON)
  -> src/moldmaker.py         (deterministic half: validate, file, commit)
  -> project store            (deposits/ + specs/ views, git ledger)
  -> brief ack back through the bridge
```

Zero stays what its own docs say it is — the **Logos/git agent**,
owner of the record. The Telegram face is a thin Pathos adapter. The
demarcation is preserved on purpose (docs/PHILOSOPHY.md, II and V).

## What is built

- **`src/moldmaker.py`** — the deposit pipeline and CLI (stdlib only).
  Init a store; deposit a transmission + interpretation as one commit
  carrying the human markdown, the A2A twin, and a commentary commit
  message; regenerate INDEX / ACTIONS / OPEN-QUESTIONS / AGENDA
  views; status and agenda commands. Enforced mechanically:
  verbatim Layer A; exact-quote/span traceability for every
  interpreted element; approval gates (inferred ≠ authorized, with
  demotions recorded, never silent); idempotent deposits; secrets
  refused; foreign dirty-tree changes refuse a deposit rather than
  being swept into it; no dates in filenames.
- **`src/interpreter.py`** — the LLM half. A strict prompt contract
  (compute the hinted calculation, mark unresolved references
  UNRESOLVED, agent-side questions become actions not user questions)
  with vault and OpenAI-compatible providers, and a validation-feedback
  channel: a failed attempt's error is fed back verbatim for retry.
- **`src/handle_telegram.py`** — payload → route → interpret →
  validate/deposit (max 3 attempts with feedback) → acknowledgement
  text (filed title, counts, first open question). A voice payload
  with no transcript returns `needs: transcription` and files nothing.
- **`.github/workflows/`** — `moldmaker-telegram.yml`
  (repository_dispatch → deposit → push → bridge reply) and
  `moldmaker-think.yml` (manual-dispatch agenda/views regeneration).
- **`tests/` + `demo.py`** — 18 acceptance tests and a no-network
  end-to-end demo (two deposits, the second a correction; a retry
  that must not duplicate).

## Fleet credit, and what was taken or refused

Built with the prepaid fleet, per the house economics (Muse
orchestrates and verifies; the fleet carries bulk):

- **MiniMax** drafted the core design. *Taken:* span-level validation
  (stronger than quote-matching), idempotency keys, refuse-on-malformed.
  *Refused:* its file layout put **dates in filenames** (violates
  ARTIFACT-SPEC) and its actions carried no approval state (violates
  the approval gate). Both were corrected in the build, not copied.
- **ZAI** ran the adversarial pass. *Taken as the test matrix:*
  traceability, idempotency ×5, malformed output → no partial commit,
  correction handling, approval gates, dirty-tree/conflict safety,
  partial failure. *Refused:* silent PII redaction — Layer A fidelity
  is the doctrine; protection is by private location and by refusing
  credentials outright, never by quietly rewriting the user's words.
- **Live-fire:** the interpreter prompt was run against MiniMax on a
  fresh dock-walking memo. First pass validated but merely restated
  the hinted calculation; the prompt was strengthened ("a
  formalization must DO the work") and the second pass computed the
  ramp angle (≈8.5°), marked the unnamed fuel-dock checker
  unresolved instead of inventing a name, and validated on attempt 1.

## What v0 does NOT do (the honest deficit)

- **Deployed, with one verification still open.** The repo is
  registered with the vault and the live Telegram bot routes
  `mold:` messages here; the first live deposit is in `dogfood/`
  (see [DEPLOYMENT.md](DEPLOYMENT.md)). Still open as of
  2026-10-21: live re-verification of the retry-idempotency fix,
  queued behind a GitHub REST rate limit on the account.
- **No native voice notes.** The bridge on hand forwards text only.
  Voice needs: bridge accepts `message.voice` → fetch audio → retain
  audio + reference → STT → payload with transcript + audio_ref.
  Dictated text works through the existing route now.
- **The think cycle is deterministic only.** Agenda/views
  regeneration is real; the LLM *"what's missing?"* completeness
  pass over the spec set is designed (docs/PROCESS.md §4) but not
  yet implemented. Nothing here pretends otherwise.
- **One store per route, minimal routing.** Chat→project mapping is
  an env JSON; there is no project-selection conversation yet.
- **No surfaces.** Phone/laptop/TV renderings (docs/SURFACES.md) are
  still design. Telegram + git are the v0 surfaces.
- **Interpretation quality is the frontier.** Validation guarantees
  traceability, not wisdom. A validated interpretation can still be
  shallow; the feedback loop and the human's corrections are the
  current corrective, and both are exercised in the tests/demo.

## Run it

```bash
python3 demo.py                                   # end-to-end, no network
python3 -m unittest discover -s tests             # 18 acceptance tests
python3 src/moldmaker.py init /path/to/store --project harbour
python3 src/moldmaker.py deposit /path/to/store \
    --text-file memo.txt --interpretation interp.json --source telegram
python3 src/moldmaker.py status /path/to/store
python3 src/moldmaker.py agenda /path/to/store
python3 src/interpreter.py --text-file memo.txt --provider vault --out interp.json
```
