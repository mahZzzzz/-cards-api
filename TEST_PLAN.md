# Test Plan — Cards Board

Source of requirements: `spec.md` (Acceptance Criteria, lines 101–111).
Source of tests: `tests/` (pytest + FastAPI `TestClient`).

All tests use an isolated temporary SQLite database provided by
`tests/conftest.py`, so the real `cards.db` is not touched.

## Latest reported test run

> **Latest reported run — not a new execution for this document.**
>
> `python -m pytest tests -q` → **92 passed, 1 warning** (12.18s).
>
> The warning is a pre-existing PyMuPDF `fitz` deprecation notice, unrelated
> to test outcomes. No pass/fail claim in this document comes from a
> re-run performed while writing it.

## Coverage by acceptance criterion

### AC1 — Creating a card

- **Requirement:** `POST /cards` returns `201`, a server-assigned ID, and status `spec`.
- **Tests:** `test_cards.py::test_create_card`, `test_create_card_with_assignee`
- **Expected result:** `201`; integer `id >= 1`; `status == "spec"`; title/description/assignee echoed back and readable via `GET /cards/{id}`.
- **Status:** Covered.

### AC2 — List, retrieve, update, delete

- **Requirement:** Cards can be listed, retrieved, updated, and deleted.
- **Tests:** `test_cards.py::test_list_cards`, `test_read_card`, `test_update_card`, `test_delete_card`, `test_root_endpoint`, `test_health_check`
- **Expected result:** `GET /cards` returns a list containing the created card; `GET /cards/{id}` returns it; `PATCH` updates only supplied fields; `DELETE` returns `204` with empty body and the card is then `404`.
- **Status:** Covered.

### AC3 — Validation and error responses

- **Requirement:** Invalid input returns `422`; illegal status changes return `409`; missing cards return `404`.
- **Tests:**
  - 422: `test_create_card_with_empty_title`, `test_invalid_card_status`, `test_status_cannot_be_null`, `test_title_length_boundary` (101 chars), `test_description_longer_than_1000_characters_is_rejected`, `test_create_card_with_missing_title_is_rejected`, `test_create_card_with_malformed_json_is_rejected`, `test_create_card_with_wrong_title_type_is_rejected`, `test_comments_assignment.py::test_reject_invalid_comment`, `test_reject_invalid_assignee`, `test_reject_invalid_assignee_on_create`
  - 409: `test_illegal_status_transition`, `test_cannot_transition_from_done`, `test_illegal_status_transitions` (16 parameterized pairs)
  - 404: `test_read_nonexistent_card`, `test_update_nonexistent_card`, `test_delete_nonexistent_card`, `test_comments_assignment.py::test_cannot_comment_on_nonexistent_card`
- **Expected result:** Exact status codes; `{"detail": "Illegal card status transition"}` for 409; `{"detail": "Card not found"}` for 404; `{"detail": "Status cannot be null"}` for null status; rejected writes leave the board unchanged.
- **Status:** Covered.

### AC4 — Full workflow

- **Requirement:** `spec → ready → in_progress → review → done` succeeds.
- **Tests:** `test_cards.py::test_complete_status_workflow`, `test_illegal_status_transitions`, `test_cannot_transition_from_done`, `test_setting_same_status_is_accepted`
- **Expected result:** Each legal step returns `200` and the new status; all 16 illegal pairs return `409` and leave the status unchanged; re-sending the current status returns `200` with an identical payload.
- **Status:** Covered.

### AC5 — Comments

- **Requirement:** Comments can be added and listed, and are removed when their card is deleted.
- **Tests:** `test_comments_assignment.py::test_add_comment_to_card`, `test_list_card_comments`, `test_reject_invalid_comment`; `test_persistence.py::test_delete_card_removes_comments_from_database`, `test_cards_comments_status_and_assignee_survive_restart`
- **Expected result:** `POST` returns `201` with `id`, `card_id`, `author`, `text`; `GET` lists them; deleting the card returns `204` and removes card and comment rows, after which both endpoints return `404`.
- **Status:** Covered.

### AC6 — Assignment

- **Requirement:** An assignee can be set, changed, and removed; blank assignees are rejected.
- **Tests:** `test_comments_assignment.py::test_create_card_with_assignee`, `test_assign_card_to_user`, `test_change_card_assignee`, `test_remove_card_assignee`, `test_reject_invalid_assignee`, `test_reject_invalid_assignee_on_create`
- **Expected result:** Setting/changing returns `200` with the new value; `"assignee": null` returns `200` with `null`; `""` and `"   "` return `422` on create and on `PATCH`.
- **Status:** Covered.

### AC7 — Persistence across restart

- **Requirement:** Cards, statuses, assignees, and comments survive a backend restart.
- **Tests:** `test_persistence.py::test_cards_comments_status_and_assignee_survive_restart`, `test_updates_survive_restart`, `test_application_startup_loads_persisted_state`, `test_tests_use_a_temporary_database`
- **Expected result:** After reloading storage from SQLite, cards, `ready` status, assignee, updated title/description, and comments are intact; a fresh application lifespan loads persisted cards; the active DB path is the temporary test DB.
- **Status:** Covered (restart simulated in-process via `reload_storage_from_db()` plus one fresh `TestClient` lifespan).

### AC8 — IDs are never reused

- **Requirement:** Deleted card and comment IDs are not reused after restart.
- **Tests:** `test_persistence.py::test_ids_are_not_reused_after_delete_and_restart`, `test_existing_database_without_counters_continues_ids`
- **Expected result:** After deleting cards/comments and reloading, the next card and comment IDs are one greater than the last issued IDs; a legacy DB without `counters` resumes from its highest stored IDs.
- **Status:** Covered.

### AC9 — Assistant and PRD preview use board state

- **Requirement:** The board assistant and PRD preview use the persisted board state.
- **Tests:** `test_assistant.py::test_assistant_searches_and_returns_real_board_data`, `test_assistant_proposes_card_creation_without_writing`, `test_create_proposal_treats_null_description_as_empty`, `test_create_proposal_omits_blank_assignee`, `test_text_only_proposal_claim_returns_no_proposal`, `test_assistant_proposes_card_move_without_writing`, `test_assistant_proposes_comment_without_writing`, `test_assistant_rejects_move_for_missing_card`, `test_assistant_rejects_illegal_status_move`, `test_assistant_rejects_invalid_card_proposal`, `test_assistant_rejects_invalid_comment_proposal`, `test_assistant_allows_only_one_proposal`, `test_llm_failure_returns_503_without_writes`, `test_llm_chat_completion_falls_back_to_next_model`, `test_endpoint_falls_back_when_primary_model_fails`; `test_prd_preview.py::test_successful_pdf_preview_with_mocked_ai`, `test_preview_does_not_create_board_cards`, `test_non_pdf_upload_is_rejected`, `test_invalid_pdf_content_is_rejected`, `test_empty_pdf_upload_is_rejected`, `test_unreadable_pdf_returns_422`, `test_oversized_pdf_is_rejected`, `test_invalid_generated_drafts_return_422`
- **Expected result:** Assistant answers from current board data through tool calls, produces read-only proposals (no automatic writes), handles tool/model failures, and returns `503` when all models fail; PRD preview returns drafts/ambiguities without creating cards and enforces `400`/`413`/`422` upload rules.
- **Status:** Partial — see gaps 6 and 7.

## Remaining coverage gaps

1. **Non-string `assignee`** (e.g. `123`) is not tested on create or `PATCH`, although the validator rejects it in `app/models.py`.
2. **`status` supplied on create** is not tested; the spec only states new cards always start as `spec`, and the current behavior is unverified.
3. **Restart realism:** persistence tests reload in-memory state rather than restarting the OS process. Only `test_application_startup_loads_persisted_state` exercises the application startup path.
4. **Persistence of an assignee removal** across reload is not tested (only assignment/change is persisted), nor is the full workflow persisted beyond `ready`.
5. **Whitespace-only comment `author`/`text`** is not tested (only `""`), and `404` on `GET /cards/{id}/comments` is tested only for a deleted card, not a never-existing card.
6. **Assistant board persistence:** assistant tests populate the board in-process and do not reload storage first, so "uses the *persisted* board state" is not directly proven.
7. **PRD duplicate detection:** `similar_cards` is always mocked to `[]`, so the PRD preview's dependency on existing board cards is not exercised.

## Out of scope of `spec.md` (tested behaviors)

Assistant proposals (`propose_*`), LLM `503` handling and model fallback, and the PRD `422` unreadable-PDF response go beyond the written acceptance criteria. They are documented here as additional safety tests, not spec requirements.
