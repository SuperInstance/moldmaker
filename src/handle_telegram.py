#!/usr/bin/env python3
"""
handle_telegram.py — the Moldmaker Telegram face (thin Pathos adapter).

This is the reroute point where the Zero agent's Telegram workflow
stops being "hear text -> brief reply" and becomes Moldmaker:

  payload -> deposit the raw transmission -> interpret (vault LLM)
          -> validate + file as a Moldmaker deposit (one commit,
             commentary included) -> brief acknowledgement for Telegram

The heavy machinery stays in the repo (Zero's demarcation: the git
agent owns the record; this face only talks to the human).

Payload (from the bridge's repository_dispatch client_payload):
  text        the transmission text (or a transcript, for voice)
  chat_id     Telegram chat id (used for project routing)
  username    sender name (recorded, never trusted as identity proof)
  message_id  Telegram message id (idempotency key)
  timestamp   ISO timestamp
  audio_ref   optional reference to retained audio (voice deposits)
  project     optional explicit project route

Routing: env MOLDMAKER_ROUTES is a JSON object {chat_id: subdir}
mapping chats to project stores inside this repo. Unmapped chats use
MOLDMAKER_DEFAULT_PROJECT (default: the repo root itself).

Output: one JSON object on stdout:
  {"ok": true, "ack_text": "...", "deposit_id": "...", "slug": "..."}
The workflow sends ack_text back through the bridge. On failure ok is
false and ack_text is a plain apology — a failed interpretation must
never produce a partial deposit (validation happens before any write).

Voice note with no transcript: returns ok=false, needs="transcription".
The bridge/STT rung is documented in docs/IMPLEMENTATION.md.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import moldmaker  # noqa: E402
import interpreter  # noqa: E402


def route_for(payload, repo_root):
    routes = {}
    raw = os.environ.get("MOLDMAKER_ROUTES", "")
    if raw:
        routes = json.loads(raw)
    sub = payload.get("project") or routes.get(str(payload.get("chat_id"))) \
        or os.environ.get("MOLDMAKER_DEFAULT_PROJECT", "")
    store = os.path.join(repo_root, sub) if sub else repo_root
    return store


def handle(payload, repo_root, interpretation=None):
    text = payload.get("text") or payload.get("transcript") or ""
    if not text.strip():
        return {"ok": False, "needs": "transcription",
                "ack_text": "I got a voice note but no transcript yet — "
                            "that rung (bridge + STT) isn't wired. Dictated "
                            "text works today."}
    store = route_for(payload, repo_root)
    moldmaker.init_store(store, project=os.path.basename(store.rstrip("/")) or "moldmaker",
                         commit=False)
    # Interpret -> validate -> deposit, with a bounded feedback loop:
    # a validation failure is fed back to the interpreter verbatim and
    # retried (max 3 attempts). A fixture interpretation (tests) is
    # never retried — it stands or falls as given.
    feedback = ""
    result = None
    for attempt in range(3):
        interp = interpretation
        if interp is None:
            interp = interpreter.interpret(text, provider="vault", feedback=feedback)
        try:
            result = moldmaker.deposit(
                store, text, interp,
                source="telegram",
                timestamp=payload.get("timestamp"),
                external_id=str(payload["message_id"]) if payload.get("message_id") else None,
                audio_ref=payload.get("audio_ref"),
            )
            break
        except moldmaker.MoldmakerError as e:
            if interpretation is not None or attempt == 2:
                raise
            feedback = str(e)
    assert result is not None
    twins = moldmaker.load_twins(store)
    twin = next(t for t in twins if t["meta"]["deposit_id"] == result["deposit_id"])
    n_actions = len(twin["actions"])
    questions = twin["questions"]
    ack = f"Filed: {twin['meta']['title']}. " \
          f"{n_actions} proposed action(s), {len(questions)} open question(s)."
    if questions:
        q = sorted(questions, key=lambda x: {"high": 0, "normal": 1, "low": 2}[x["priority"]])[0]
        ack += f" First question when you're ready: {q['question']}"
    if not result["created"]:
        ack = f"Already filed (deposit {result['deposit_id']}). Nothing duplicated."
    return {"ok": True, "ack_text": ack, **result}


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description="Moldmaker Telegram handler")
    p.add_argument("--payload", required=True, help="client_payload JSON file")
    p.add_argument("--repo-root", default=".")
    p.add_argument("--interpretation", help="fixture interpretation JSON (testing; skips LLM)")
    args = p.parse_args(argv)

    with open(args.payload) as f:
        payload = json.load(f)
    interp = None
    if args.interpretation:
        with open(args.interpretation) as f:
            interp = json.load(f)
    try:
        out = handle(payload, os.path.abspath(args.repo_root), interp)
    except Exception as e:
        out = {"ok": False, "error": str(e),
               "ack_text": "Something broke filing that — nothing was "
                           "committed. The error is in the workflow log."}
    print(json.dumps(out))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
