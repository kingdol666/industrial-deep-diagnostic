# Ontology model management — end-to-end UI verification

Drives the **running** GUI (frontend :5180 → backend :3210) through the full
ontology lifecycle a user performs, and cross-checks every UI action against the
server state through the REST API.

## Why it exists

Unit and HTTP tests prove the API is correct. They cannot prove the page renders,
that the graph canvas actually has pixels, that clicking a node fills the
inspector, or that a field edited in a form reaches disk. This script closes that
gap: **31 assertions over real browser + real backend**.

## Prerequisites

```bash
node commands/cli.mjs start --all --detach     # backend 3210 + frontend 5180
```

An account on the running instance (defaults to `ontoadmin` / `OntoAdmin123!`).
Create one with:

```bash
curl -X POST http://127.0.0.1:3210/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"ontoadmin","password":"OntoAdmin123!","email":"ontoadmin@local.test"}'
```

## Run

```bash
python tests/e2e/ontology-ui-e2e.py
```

Exit code 0 = all checks passed. A full-page screenshot is written to
`.runtime/ontology-page.png`.

## What it asserts

login → ontology tab → asset list → graph canvas has real size → knowledge-layer
toggle adds categories → graph click fills the inspector → structure editor renders
signal cards → edit a field marks the draft dirty → CP-2 validate runs → save
creates a **new** server-side version → the edited semantics are the ones the
server now holds → the parent version is recorded → the history version is
untouched → reload still shows the new version → version diff contains the edited
field path → model-health renders a score with breakdown → adopt-candidates modal
lists the agent-built run-dir ontologies with CP-2 verdicts → create-ontology modal
opens → zero uncaught console/page errors.

## Note on repetition

The test writes a **unique** marker each run (`EDIT_MARK` embeds a timestamp).
Saving identical content is deduplicated server-side by design, so a fixed marker
would correctly produce no new version on a second run and the assertions would
fail — that dedup is a feature, not a bug being worked around.
