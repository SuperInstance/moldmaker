#!/usr/bin/env python3
"""
interpreter.py — produce a Moldmaker interpretation for a transmission.

The interpreter is the LLM half of the pipeline; src/moldmaker.py is the
deterministic half that validates whatever this produces. The contract
between them is the JSON schema described in build_prompt() and enforced
by moldmaker.validate_interpretation:

  - every section/intent/action traces to an EXACT quote of the raw
    transmission (or an explicit span);
  - inferences are marked as inferences, with confidence;
  - names the user did not say are never invented — unresolved
    references stay unresolved and become questions or open items;
  - actions are proposals. Nothing here can approve anything.

Providers:
  vault   — the SuperInstance vault proxy (service "llm", action
            "complete"), the same route the Zero agent uses. Needs
            VAULT_URL and OIDC_TOKEN in the environment.
  openai  — any OpenAI-compatible chat endpoint. Needs LLM_API_URL,
            LLM_MODEL; LLM_API_KEY optional.

Usage:
  interpreter.py --text-file memo.txt --provider vault --out interp.json
  interpreter.py --text "raw transmission..." --provider openai
"""

import argparse
import json
import os
import sys
import urllib.request

SYSTEM_PROMPT = """You are the interpretation step of Moldmaker. You turn a \
person's raw transmission into a formal, traceable interpretation. You are \
not the author of their words and you must not improve them. Your output is \
validated mechanically: any element that cannot be traced to an exact quote \
of the transmission will be rejected."""

SCHEMA_DESCRIPTION = """Return ONE JSON object, no prose around it:
{
  "title": "short human title for this transmission",
  "sections": [
    {"heading": "topic heading",
     "source_quote": "EXACT substring of the transmission",
     "annotations": [
       {"kind": "note|inference|formalization|context|action|question",
        "basis": "said|inferred|context",
        "text": "what this passage means for the project",
        "confidence": 0.0-1.0 (for inferences),
        "source_ref": "required only when basis is context: where the injected context came from"}
     ]}
  ],
  "intents": [
    {"id": "intent.slug", "kind": "requirement|decision|problem|preference|instruction",
     "statement": "the formal version of what the person intends",
     "source_quote": "EXACT substring", "confidence": 0.0-1.0, "status": "proposed"}
  ],
  "actions": [
    {"id": "action.slug", "title": "work an agent could do",
     "owner": "logic-agent|hardware-agent|research-agent|human|unspecified",
     "source_quote": "EXACT substring", "confidence": 0.0-1.0, "status": "proposed"}
  ],
  "questions": [
    {"id": "question.slug", "question": "a question only the user can settle",
     "why": "why the answer would change the build",
     "priority": "high|normal|low", "source_quote": "EXACT substring or null"}
  ],
  "commentary": {
    "tone": "the tone of the transmission, briefly",
    "meaning": "what this means, in your judgment",
    "salience": "why you found the important parts important",
    "connections": ["connections to other work, as strings"]
  }
}
Rules:
- source_quote values must be copied character-for-character from the transmission.
- A "formalization" annotation must DO the work, not restate the request:
  a hinted calculation gets computed (show the formula and the number), a
  hinted reference gets resolved or explicitly marked unresolved, a hinted
  equation gets written out. Restating what the person asked for is a failed
  formalization.
- If the transmission contains an unresolved reference ("whoever", "that
  thing"), an annotation must explicitly mark it UNRESOLVED. Never guess it
  into a name.
- Never invent a name, date, or fact the person did not state. If a reference
  is unresolved ("whoever", "that thing"), leave it unresolved and say so in
  an annotation.
- Agent-side questions (things agents can find out themselves) become
  actions for the relevant agent, NOT questions for the user.
- Questions for the user are a budget: include only questions whose answers
  would change the build.
- Actions always have status "proposed". You cannot approve anything."""


def build_prompt(raw, context="", feedback=""):
    parts = [SCHEMA_DESCRIPTION, "", "TRANSMISSION:", raw]
    if context:
        parts += ["", "CONTEXT FROM THE RECORD (may inform 'context' annotations "
                      "with source_ref naming this material):", context]
    if feedback:
        parts += ["", "A PREVIOUS ATTEMPT AT THIS INTERPRETATION FAILED "
                      "MECHANICAL VALIDATION with this error — fix exactly "
                      f"that, and re-check every quote character-for-character: {feedback}"]
    return "\n".join(parts)


def extract_json(text):
    """Pull the first complete JSON object out of a model reply."""
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in model reply")
    obj, _end = json.JSONDecoder().raw_decode(text[start:])
    if not isinstance(obj, dict):
        raise ValueError("model reply JSON is not an object")
    return obj


def _post_json(url, payload, headers=None, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


DEFAULT_VAULT_URL = "https://superinstance-vault.casey-digennaro.workers.dev"


def vault_base_url():
    # An env var set to "" (e.g. a GitHub workflow expanding an unset
    # repo variable) must fall back to the default, not become the URL.
    # First live deployment failed exactly here: POST "/proxy".
    return os.environ.get("VAULT_URL") or DEFAULT_VAULT_URL


def interpret_vault(raw, context="", model=None, feedback=""):
    vault_url = vault_base_url()
    oidc = os.environ.get("OIDC_TOKEN", "")
    if not oidc:
        raise RuntimeError("OIDC_TOKEN not set (vault provider needs it)")
    data = _post_json(f"{vault_url}/proxy", {
        "oidc_token": oidc,
        "service": "llm",
        "action": "complete",
        "params": {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_prompt(raw, context, feedback)},
            ],
            **({"model": model} if model else {}),
        },
    })
    r = data.get("result", data)
    text = r.get("content") or r.get("text") or ""
    if not text and isinstance(r, str):
        text = r
    return extract_json(text)


def interpret_openai(raw, context="", model=None, feedback=""):
    url = os.environ.get("LLM_API_URL", "")
    if not url:
        raise RuntimeError("LLM_API_URL not set (openai provider needs it)")
    headers = {}
    key = os.environ.get("LLM_API_KEY", "")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    data = _post_json(url, {
        "model": model or os.environ.get("LLM_MODEL", "default"),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(raw, context, feedback)},
        ],
    }, headers=headers)
    text = data["choices"][0]["message"]["content"]
    return extract_json(text)


def interpret(raw, provider="vault", context="", model=None, feedback=""):
    if provider == "vault":
        return interpret_vault(raw, context, model, feedback)
    if provider == "openai":
        return interpret_openai(raw, context, model, feedback)
    raise ValueError(f"unknown provider {provider!r}")


def main(argv=None):
    p = argparse.ArgumentParser(description="Moldmaker interpreter (LLM half)")
    p.add_argument("--text")
    p.add_argument("--text-file")
    p.add_argument("--context-file")
    p.add_argument("--provider", default="vault", choices=["vault", "openai"])
    p.add_argument("--model")
    p.add_argument("--out")
    args = p.parse_args(argv)

    raw = args.text
    if args.text_file:
        with open(args.text_file) as f:
            raw = f.read()
    if not raw or not raw.strip():
        print("ERROR: empty transmission", file=sys.stderr)
        return 1
    context = ""
    if args.context_file:
        with open(args.context_file) as f:
            context = f.read()
    try:
        interp = interpret(raw, args.provider, context, args.model)
    except Exception as e:
        print(f"ERROR: interpretation failed: {e}", file=sys.stderr)
        return 1
    out = json.dumps(interp, indent=2) + "\n"
    if args.out:
        with open(args.out, "w") as f:
            f.write(out)
    else:
        print(out, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
