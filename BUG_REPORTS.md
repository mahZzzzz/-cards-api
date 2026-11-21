# Bug Reports — Cards Board

Scope: defects encountered during development of the Cards Board
(FastAPI + SQLite + vanilla JS frontend). Each report is based on the
current repository code and tests, plus the development history described
in the project brief.

Evidence basis:

- Code: `app/main.py`, `database.py`, `assistant_service.py`, `frontend/app.js`, `frontend/index.html`.
- Automated tests: `tests/test_persistence.py`, `tests/test_assistant.py`.
- **Latest reported run (not re-executed for this document):** `pytest tests` → **92 passed, 1 warning**.
- Manual observations are labeled as such. No screenshots, dates, or commit references are included.

---

## BUG-1 — Cards lost after backend restart (pre-persistence)

**Severity:** High — user data loss.

**Status:** Fixed and verified by automated tests.

### Steps to reproduce (historical)

1. Start the backend.
2. Create one or more cards through `POST /cards`.
3. Stop the backend, then start it again.
4. Request `GET /cards`.

### Expected behavior

Cards created before the restart remain available with their title,
description, status, and assignee.

### Actual observed behavior

After the restart the board was empty: all cards created in the previous
process were gone.

### Root cause

Cards were held only in the process-local `cards` dictionary in
`app/main.py` (still annotated as "Temporary in-memory storage"). Nothing
was written to disk, so terminating the process discarded all card and
comment state.

### Fix applied

- Added the SQLite layer in `database.py` with `cards`, `comments`, and
  `counters` tables, plus `initialize_database()`.
- Card and comment writes are persisted immediately (`database.create_card`,
  `save_card`, `create_comment`, `delete_card`).
- IDs are tracked in the `counters` table and initialized from the highest
  stored IDs when a legacy database has no counters.
- On startup, `initialize_storage()` creates the schema and
  `reload_storage_from_db()` hydrates the in-memory cache from SQLite.
- Tests use an isolated temporary database via `tests/conftest.py`; the real
  `cards.db` is not modified.

### Verification evidence

Automated:

- `tests/test_persistence.py::test_cards_comments_status_and_assignee_survive_restart`
- `tests/test_persistence.py::test_updates_survive_restart`
- `tests/test_persistence.py::test_application_startup_loads_persisted_state`
- `tests/test_persistence.py::test_delete_card_removes_comments_from_database`
- `tests/test_persistence.py::test_ids_are_not_reused_after_delete_and_restart`
- `tests/test_persistence.py::test_existing_database_without_counters_continues_ids`
- `tests/test_persistence.py::test_tests_use_a_temporary_database`

These are included in the latest reported run (92 passed, 1 warning).

Note: restart is simulated in-process with `reload_storage_from_db()`, plus
one test that opens a fresh application lifespan. A real OS-level process
restart is not exercised automatically.

---

## BUG-2 — Assistant Confirm/Cancel buttons missing in the browser

**Severity:** Medium — proposal flow unusable from the UI; no data loss or
incorrect write.

**Status:** Fixed.

### Steps to reproduce

1. Open the frontend in a browser that had loaded an earlier `app.js`.
2. Ask the assistant to create a card (or move/comment).
3. The API response contains a structured `proposal`.
4. The chat shows the assistant reply, but no "Confirm this change" panel and
   no Confirm/Cancel buttons appear.

### Expected behavior

When `POST /assistant/chat` returns a `proposal`, the UI renders a confirmation
panel with **Confirm** and **Cancel** buttons and disables further chat input
until the user decides.

### Actual observed behavior

The reply text was displayed, but the proposal panel and both buttons were
absent, making the proposed change impossible to confirm or cancel.

### Root cause

The browser was running a stale cached copy of `frontend/app.js` that did not
contain the proposal rendering code. The backend was returning the structured
proposal correctly; the loaded script simply never called `renderProposal`.

### Fix applied

- Current `frontend/app.js` renders the panel whenever `data.proposal` is
  present (`renderProposal`), including the Confirm/Cancel handlers and the
  `submitProposal` call to the Cards API.
- `frontend/index.html` loads the script with a cache-busting version query:
  `<script src="app.js?v=2"></script>`.

### Verification evidence

Automated (API side only):

- `tests/test_assistant.py::test_assistant_proposes_card_creation_without_writing` — asserts the API returns `proposal.action == "create_card"` and performs no write.
- `tests/test_assistant.py::test_assistant_proposes_card_move_without_writing`
- `tests/test_assistant.py::test_assistant_proposes_comment_without_writing`

Code inspection:

- `frontend/app.js` — `renderProposal` creates the "Confirm this change" panel
  and both buttons; `assistantChatForm` calls it on `data.proposal`.
- `frontend/index.html` — versioned script URL.

Manual: the end-to-end browser behavior was checked during development after
the cache-busting change. This project has no automated frontend/DOM tests, so
button rendering is not covered by pytest.

---

## BUG-3 — Assistant claimed a proposal without calling a propose_* tool

**Severity:** Medium — misleading UX and blocked workflow; no incorrect write
occurred (proposals are never auto-applied).

**Status:** Mitigated; residual model-behavior risk remains.

### Steps to reproduce

1. Ask the assistant to create, move, or comment on a card.
2. The language model replies in text such as "I prepared a create-card
   proposal. Please confirm it." without emitting a `propose_*` tool call.

### Expected behavior

Either the assistant calls the matching `propose_*` tool and the API returns a
structured `proposal`, or it answers honestly without claiming a proposal
exists. A proposal must never be asserted in prose alone.

### Actual observed behavior

The reply claimed a proposal was ready, but the API response contained no
`proposal` object, so the frontend had nothing to render and no Confirm/Cancel
panel appeared. No board changes were made.

### Root cause

The language model occasionally ignored the tool-use instruction and described
a proposal in natural language. The backend intentionally builds proposals
only from validated `propose_*` tool results; it does not parse prose into
proposals. The prose claim therefore had no structured counterpart.

### Fix applied

- `assistant_service.SYSTEM_PROMPT` now states explicitly that a proposal
  requires the matching `propose_*` tool call, that the assistant must never
  claim a proposal is ready unless the tool call succeeded, and that it must
  not claim a change was made before confirmation.
- `answer_board_request` returns a proposal only when a `propose_*` tool call
  validates successfully; invalid arguments, missing cards, illegal status
  moves, and a second proposal return tool errors instead.
- The frontend renders Confirm/Cancel only when the API response actually
  contains `proposal`.
- A regression test locks in the behavior for a text-only claim.

### Verification evidence

Automated:

- `tests/test_assistant.py::test_text_only_proposal_claim_returns_no_proposal` — the API returns the reply text, omits `proposal`, and leaves `/cards` unchanged.
- `tests/test_assistant.py::test_assistant_rejects_invalid_card_proposal`
- `tests/test_assistant.py::test_assistant_rejects_invalid_comment_proposal`
- `tests/test_assistant.py::test_assistant_rejects_move_for_missing_card`
- `tests/test_assistant.py::test_assistant_rejects_illegal_status_move`
- `tests/test_assistant.py::test_assistant_allows_only_one_proposal`

All are included in the latest reported run (92 passed, 1 warning). The tests
mock the LLM, so they verify the API's behavior for a given model output, not
the model's tendency to make such claims.

Residual risk: prompt instructions cannot guarantee third-party model
compliance. The API now fails safe (no proposal, no write) when the model only
claims one in text.

---

## Summary

| ID | Issue | Severity | Status |
|---|---|---|---|
| BUG-1 | Cards lost after backend restart | High | Fixed — automated coverage |
| BUG-2 | Confirm/Cancel missing due to stale `app.js` | Medium | Fixed — API covered; UI verified manually |
| BUG-3 | Text-only proposal claim without tool call | Medium | Mitigated — regression test; model compliance not guaranteed |

Latest reported test run: **92 passed, 1 warning** (not re-executed for this
document).
