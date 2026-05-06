---
name: redmine
description: Use this skill whenever the user wants to query, create, update, or otherwise interact with their Redmine instance — issues/tickets, projects, time entries, wiki pages, users, custom fields. Trigger on any mention of "Redmine", "Ticket", "Aufgabe in Redmine", "remi.bc-management.eu", or when the user references issue IDs (e.g. "#8796"), project slugs, or asks things like "welche offenen Aufgaben habe ich", "leg ein Ticket an", "buche Zeit auf …", "was läuft im Projekt X". The skill bundles the user's `.env` (URL + API token) and the Redmine `openapi.json` spec in its own folder, so trigger this skill rather than reaching for a generic HTTP/curl approach.
---

# Redmine API Skill

Helps you interact with the user's Redmine instance through the REST API. The OpenAPI spec (`openapi.json`) and credentials (`.env`) are bundled in this skill's own folder — always read them from there. Don't invent endpoints or parameter names; verify against `openapi.json` whenever you're unsure.

## Setup — credentials and base URL

Both files are bundled in this skill's own directory, alongside `SKILL.md`:

- `.env` — contains `URL=…` (with trailing slash) and `TOKEN=…` (the Redmine API key). On first install this file is **not** present — copy `.env.example` to `.env` and fill in the URL and token.
- `openapi.json` — full Redmine 6.1 OpenAPI 3 spec, the source of truth for endpoints, parameters, and schemas

Refer to them via the directory of this skill — don't hard-code an absolute host path, and don't assume the user's working directory. In bash, derive it once and reuse it:

```bash
SKILL_DIR="$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$BASH_SOURCE")")"
# or, if you know the skill path from the loader, use it directly:
SKILL_DIR="/path/to/skills/redmine"   # set by whoever invokes the skill
```

**Loading the env** (use this exact pattern; `set -a` exports everything `.env` defines so it's visible to `curl`):

```bash
set -a && . "$SKILL_DIR/.env" && set +a
```

When the skill runs inside Cowork or Claude Code, the user usually mentions where the skill folder lives, or the loader passes it in. If neither is available, ask the user for the path rather than guessing — the credentials are sensitive and you don't want to read a stale `.env` from a different directory.

**Auth header** — Redmine accepts the API key in two ways. Prefer the header so the token never lands in shell history or server logs as a query parameter:

```bash
curl -sS -H "X-Redmine-API-Key: $TOKEN" "${URL}issues.json?…"
```

Never put `key=$TOKEN` in the URL. Never echo `$TOKEN` in your output to the user.

## How to look up an endpoint

Before writing a request, check the spec. The path keys are templated (`{format}` is `json` or `xml` — always use `json`):

```bash
# list all paths
jq -r '.paths | keys[]' "$SKILL_DIR/openapi.json"

# inspect parameters for a specific endpoint
jq -r '.paths["/issues.{format}"].get.parameters[]? | "\(.name): \(.description)"' "$SKILL_DIR/openapi.json"

# inspect the request body schema for a POST/PUT
jq '.paths["/issues.{format}"].post.requestBody.content["application/json"].schema' "$SKILL_DIR/openapi.json"
```

This is faster and more reliable than guessing parameter names — Redmine's filter syntax has subtle operators (`=`, `!`, `o`, `c`, `*`, `!*`, `><`, `>=`, …) that vary per field.

## The most useful endpoints

`GET /issues.json` is the workhorse — almost every "what's going on" question lands here. Other routes worth knowing:

- `GET /users/current.json` — who am I (returns `id`, `login`, useful when an endpoint needs `user_id`)
- `GET /projects.json` — all visible projects; use `?include=trackers,issue_categories` for richer output
- `GET /issues/{id}.json?include=journals,attachments,relations,children,watchers` — full detail for one ticket
- `POST /issues.json` — create a ticket
- `PUT /issues/{id}.json` — update status, assignee, notes (notes go in `issue.notes`, they become a journal comment)
- `GET /time_entries.json?user_id=me&from=YYYY-MM-DD&to=YYYY-MM-DD` — time tracking
- `POST /time_entries.json` — book hours
- `GET /issue_statuses.json` and `GET /trackers.json` — to translate IDs ↔ names
- `GET /search.json?q=…` — global full-text search

## Filtering issues — the patterns you'll need most

Redmine's `assigned_to_id`, `status_id`, etc. accept either an ID, a list joined with `|`, the special value `me`, or an operator-prefixed expression. The most common recipes:

```bash
# Open issues assigned to me, urgent first, newest first
"${URL}issues.json?assigned_to_id=me&status_id=open&sort=priority:desc,updated_on:desc&limit=100"

# All issues in a project, including closed
"${URL}issues.json?project_id=zeichentool-3-0&status_id=*&limit=100"

# Issues updated in the last 7 days (any status)
"${URL}issues.json?updated_on=%3E%3D2026-04-29&status_id=*"   # %3E%3D = >=

# Issues NOT assigned to anyone, in any open status
"${URL}issues.json?assigned_to_id=!*&status_id=open"

# Full-text search ("contains all words")
"${URL}issues.json?any_searchable=~bildupload"
```

**Critical Redmine quirk:** `status_id=open` filters out only statuses configured as "closed" in the workflow. A status named "Gelöst" / "Resolved" is often still considered *open* — it shows up in `assigned_to_id=me&status_id=open` even though semantically the work is done. When the user asks "what's open", report this honestly: list everything, but flag tickets in resolved-style statuses separately so the user can see what's truly waiting on them vs. what's just awaiting final closure.

To check which statuses are actually closed:

```bash
curl -sS -H "X-Redmine-API-Key: $TOKEN" "${URL}issue_statuses.json" \
  | jq '.issue_statuses[] | {id, name, is_closed}'
```

## Creating and updating issues

Redmine wraps the body in a top-level `issue` (or `time_entry`, `project`, …) key. Forgetting the wrapper is the #1 reason POSTs come back with cryptic errors.

```bash
# Create
curl -sS -X POST -H "X-Redmine-API-Key: $TOKEN" -H "Content-Type: application/json" \
  "${URL}issues.json" \
  -d '{
    "issue": {
      "project_id": 42,
      "subject": "Kurzbeschreibung",
      "description": "Details …",
      "tracker_id": 1,
      "priority_id": 2,
      "assigned_to_id": 45
    }
  }'

# Update — status change with a comment in one call
curl -sS -X PUT -H "X-Redmine-API-Key: $TOKEN" -H "Content-Type: application/json" \
  "${URL}issues/8796.json" \
  -d '{"issue": {"status_id": 3, "notes": "Behoben in Release 2.4."}}'
```

`PUT` returns `204 No Content` on success — no body. Don't try to parse the response; check the status code or do a follow-up `GET` if you need to confirm the change.

## Pagination

Default `limit` is 25, max 100. The response carries `total_count`, `offset`, `limit` — loop until `offset + count >= total_count`:

```bash
offset=0
while :; do
  page=$(curl -sS -H "X-Redmine-API-Key: $TOKEN" \
    "${URL}issues.json?assigned_to_id=me&status_id=*&limit=100&offset=$offset")
  echo "$page" | jq '.issues[]'
  total=$(echo "$page" | jq '.total_count')
  offset=$((offset + 100))
  [ $offset -ge $total ] && break
done
```

For one-off lookups just set `limit=100` and check that `count == total_count` — if it does, you have everything; if not, mention to the user that there are more results.

## Reporting results to the user

When listing issues, group by what the user actually cares about (priority, project, due date) rather than dumping raw JSON. A useful default shape:

- Group urgent / overdue items first
- For each: `#ID — Project / Tracker — "Subject" — Status — Due date — % done`
- Flag "Gelöst"/"Resolved"-style statuses as a separate group with a note that they're technically still open
- Don't print the API key, the full response, or every field — just what's relevant

For larger result sets the user will revisit (open tickets, sprint board, time-tracking dashboard), offer to turn it into a live artifact with `mcp__cowork__create_artifact` so they can refresh it without re-asking.

## Common gotchas

- **Trailing slash in URL.** `.env` has `URL=https://…/` — concatenate with the bare path (`${URL}issues.json`), don't add another slash.
- **`me` only works inside filters**, not as a value for `user_id` on time entries. For `time_entries.json?user_id=…` you need the numeric ID — fetch it once via `users/current.json`.
- **Custom fields** come back as `custom_fields: [{id, name, value}]`. To filter by them, use `cf_<id>=value` as a query parameter — the ID, not the name.
- **Date filters** use ISO `YYYY-MM-DD`. Operators are URL-encoded: `>=` is `%3E%3D`, `<=` is `%3C%3D`, `><` (between) is `%3E%3C` with values pipe-separated.
- **Permission errors** return 403 with a tiny body. If a query the user expects to work returns nothing, also check whether the API user actually has access to the project.
- **`include=` is comma-separated, no spaces**: `include=journals,attachments,relations`. Wrong separator → silently ignored.

## When to fall back to the OpenAPI spec

If the user asks about something not covered above — wiki pages, repository revisions, project memberships, file uploads, queries, enumerations — go straight to `openapi.json` and read the relevant section before constructing the request. The spec has the full parameter list and response schema for every route, and it's faster to read than to guess and retry.
