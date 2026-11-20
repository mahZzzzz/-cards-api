# Cards Board Specification

## Purpose

The Cards Board is a small project-management application for tracking task cards through a fixed workflow. It provides a FastAPI REST API, a SQLite persistence layer, and a vanilla JavaScript Kanban-style frontend.

The board lets users create cards, move them through stages, assign an owner, and add comments. Data is stored in SQLite and survives backend restarts.

## Card Fields

| Field | Type | Rules |
|---|---|---|
| `id` | integer | Assigned by the server; never reused. |
| `title` | string | Required; 1–100 characters. |
| `description` | string | Optional on create; defaults to `""`; maximum 1000 characters. |
| `status` | enum | `spec`, `ready`, `in_progress`, `review`, or `done`; new cards start as `spec`. |
| `assignee` | string or null | Optional; `null` means unassigned; empty or whitespace-only values are rejected. |

## Statuses and Transitions

Allowed transitions:

| From | To |
|---|---|
| `spec` | `ready` |
| `ready` | `in_progress` |
| `in_progress` | `review` |
| `review` | `done` |
| `done` | none |

Forbidden transitions:

- Moving backwards, such as `review` → `in_progress`.
- Skipping stages, such as `spec` → `done`.
- Any transition away from `done`.
- Any status value outside the five defined values.

An illegal transition returns HTTP `409` with `{"detail": "Illegal card status transition"}`. Submitting the card's current status is accepted and leaves the status unchanged.

## API Endpoints

| Method | Endpoint | Behavior |
|---|---|---|
| GET | `/` | Returns a running message. |
| GET | `/health` | Returns `{"status": "ok"}`. |
| GET | `/cards` | Lists all cards. |
| POST | `/cards` | Creates a card; returns `201`; status is always `spec`. |
| GET | `/cards/{card_id}` | Returns one card; `404` if missing. |
| PATCH | `/cards/{card_id}` | Updates any supplied card fields; omitted fields stay unchanged; `404` if missing. |
| DELETE | `/cards/{card_id}` | Deletes the card and its comments; returns `204`; `404` if missing. |
| POST | `/cards/{card_id}/comments` | Adds a comment; returns `201`; `404` if the card is missing. |
| GET | `/cards/{card_id}/comments` | Lists the card's comments; `404` if the card is missing. |
| POST | `/prd/preview` | Uploads a PDF and returns draft cards and ambiguities; does not save cards. |
| POST | `/assistant/chat` | Answers a read-only question about the board using `{"message": "..."}` and returns `{"reply": "..."}`. |

## Validation and Error Rules

### HTTP 422 — Invalid request data

- Missing or empty `title`; title longer than 100 characters.
- Description longer than 1000 characters.
- Invalid `status` value.
- Explicitly null `status` on update; detail is `"Status cannot be null"`.
- Empty or whitespace-only `assignee`.
- Comment `author` or `text` shorter than 1 character.
- Malformed request bodies or wrong field types.

### HTTP 409 — Illegal status transition

- Any transition not listed in the allowed table.

### Other errors

- `404` — card not found, including comment operations on a missing card.
- `400` — PRD upload is not a PDF or is not a valid PDF.
- `413` — PRD upload exceeds 10 MB.

## Comments and Assignment

**Comments**
- A comment has `id`, `card_id`, `author`, and `text`.
- `author` and `text` are required and must contain at least one character.
- Comments belong to an existing card.
- Deleting a card also deletes its comments.

**Assignment**
- `assignee` may be set when creating a card.
- `PATCH /cards/{card_id}` can assign, change, or remove the assignee.
- Sending `"assignee": null` removes the assignment.
- Blank or whitespace-only assignees return `422`.

## SQLite Persistence

- Data is stored in `cards.db` using the `cards`, `comments`, and `counters` tables.
- On startup, the schema is initialized and persisted cards and comments are loaded into the application.
- Card and comment writes are persisted immediately, so data survives backend restarts.
- Card and comment IDs are tracked in the `counters` table and are never reused after deletion or restart. Existing databases without counters are initialized from their highest stored IDs.
- Deleting a card removes the card and its comments in one database transaction.
- Automated tests use isolated temporary SQLite databases and do not modify the real `cards.db`.

## Acceptance Criteria

- [ ] Creating a card returns `201`, a server-assigned ID, and status `spec`.
- [ ] Cards can be listed, retrieved, updated, and deleted.
- [ ] Invalid input returns `422`; illegal status changes return `409`; missing cards return `404`.
- [ ] The full `spec → ready → in_progress → review → done` workflow succeeds.
- [ ] Comments can be added and listed, and are removed when their card is deleted.
- [ ] An assignee can be set, changed, and removed; blank assignees are rejected.
- [ ] Cards, statuses, assignees, and comments survive a backend restart.
- [ ] Deleted card and comment IDs are not reused after restart.
- [ ] The board assistant and PRD preview use the persisted board state.
