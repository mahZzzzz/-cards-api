# Architecture & Security Checklist — Cards Board

Project: FastAPI + SQLite Cards Board with Board Assistant, PRD preview, and a vanilla-JS frontend.
Scope of this document: OWASP Top 10 assessment of the existing code. **No security fixes are implemented here.**

Basis: read-only inspection of `app/main.py`, `app/models.py`, `database.py`,
`assistant_service.py`, `prd_service.py`, `importer.py`, `llm.py`,
`frontend/app.js`, `frontend/index.html`, `requirements.txt`,
`.github/workflows/tests.yml`, `.gitignore`, `README.md`.

Status legend: **Mitigated** = a control already exists in code; **Open** = no control yet; **Not applicable** = no exposure path found.
Assessment legend: **Confirmed** = verified by inspection; **Potential** = exposure exists but exploitability depends on deployment or third-party libraries.

Deployment context: the documented run command is local (`README.md:48`,
`uvicorn app.main:app --reload`, default `127.0.0.1`). Severity below assumes the API could become reachable beyond localhost.

---

## OWASP Top 10 checklist

### A01 — Broken Access Control

- **Locations:** every route in `app/main.py:108-387` is public; no auth dependency or middleware. CORS is configured at `app/main.py:44-54`. Card IDs are sequential and enumerable.
- **Assessment:** Confirmed absence of authentication/authorization. CORS restricts browser origins only; it is not access control for direct HTTP clients.
- **Status:** **Open**. **Severity:** Medium–High if network-exposed; Low for localhost-only use.
- **Risk:** Anyone who can reach the port can read, create, update, or delete any card/comment, upload PRDs, and consume LLM quota.
- **Minimal mitigation:** Keep the app bound to `127.0.0.1` and state this constraint; once user accounts exist (Days 18–19), enforce per-user ownership on every `/cards/{id}` and `/cards/{id}/comments` route.

### A02 — Cryptographic Failures

- **Locations:** SQLite file `cards.db` (`database.py:5`, schema `71-110`); frontend base URL is HTTP (`frontend/app.js:2`); API key read from environment (`llm.py:50,105`).
- **Assessment:** Potential, deployment-dependent. Card data is stored unencrypted at rest and traffic is plain HTTP. `.env` and `cards.db` are git-ignored (`.gitignore:10,31`) and untracked.
- **Status:** **Open** (at-rest/transport protection not implemented). **Severity:** Low locally; Medium if exposed.
- **Minimal mitigation:** Keep secrets in `.env` only; if the course requires remote access, terminate TLS in front of the API and restrict database file permissions/backups. No secret is currently returned by any endpoint.

### A03 — Injection

- **SQL injection — Mitigated.** All SQL uses bound parameters (`database.py:120-134`, `151-170`, `195-218`, `243-249`). The only f-string SQL is `database.py:22`, invoked with internal constant table names (`database.py:107-108`), never user input.
- **XSS — Mitigated.** Frontend writes card, comment, PRD, and assistant content with `textContent`/`replaceChildren` (`frontend/app.js:32-35`, `132-140`, `458-461`, `587-603`, `752`). `innerHTML` is used only to clear a list (`frontend/app.js:17`). No DOM injection sink found.
- **Prompt injection — Open.** Card titles/descriptions are sent to the model (`assistant_service.py:229-237`, `367-379`), as is extracted PDF text (`prd_service.py:52-90`). The prompts instruct the model to treat this as untrusted data (`assistant_service.py:17-45`, `prd_service.py:65-67`), but that is advisory.
- **Assessment:** Confirmed exposure for prompt injection; impact is bounded by server-side validation and explicit confirmation. **Status:** **Open** for prompt injection only. **Severity:** Medium.
- **Minimal mitigation:** Clearly delimit/quote untrusted text in tool results and PDF prompts; keep proposal validation server-side; never auto-execute model proposals.

### A04 — Insecure Design (resource abuse)

- **Locations:** unbounded assistant input (`app/main.py:345-347`); unbounded comment `author`/`text` (`app/models.py:66-69`); unbounded `assignee` (`app/models.py:23-30`); no rate limiting on `/assistant/chat` (`app/main.py:354-387`) or `/prd/preview` (`app/main.py:288-342`, OCR/LLM work in `prd_service.py:26-100`).
- **Assessment:** Confirmed missing bounds/quotas. Title and description are capped (`app/models.py:33-36`, `44-48`); the PRD upload is capped at 10 MB (`app/main.py:295-312`), which limits but does not remove parser/CPU cost.
- **Status:** **Open**. **Severity:** Medium (availability and LLM cost).
- **Minimal mitigation:** Add `max_length` to assistant message, comment fields, and assignee; add a small fixed-window rate limit to the two expensive endpoints. The confirmation flow already prevents silent writes.

### A05 — Security Misconfiguration

- **Locations:** CORS `app/main.py:44-54` (narrow localhost origins, credentials disabled — reasonable); no CSP/security headers; dev `--reload` command in `README.md:48`; broad `except Exception` → 503 without logging at `app/main.py:371-385`.
- **Assessment:** Potential. No critical misconfiguration found, but there is no environment separation or deployment hardening guidance.
- **Status:** **Open** (hardening/documentation). **Severity:** Low.
- **Minimal mitigation:** Document a production run command (no `--reload`), narrow the assistant exception handler, and add basic response headers only if the frontend is served by the API.

### A06 — Vulnerable and Outdated Components

- **Locations:** `requirements.txt` pins top-level packages but not transitives; CI installs without audit or hashes (`.github/workflows/tests.yml:24-32`).
- **Assessment:** Confirmed process gap; no specific vulnerable version verified in this review (no external CVE lookup performed).
- **Status:** **Open**. **Severity:** Low–Medium.
- **Minimal mitigation:** Add `pip-audit` to CI and maintain a full pinned lock file from the working environment.

### A07 — Identification and Authentication Failures

- **Locations:** no login, session, token, or user model anywhere in `app/main.py`; the assistant and PRD endpoints are equally open (`app/main.py:288-387`).
- **Assessment:** Confirmed absence of authentication (same root cause as A01). No password storage exists yet, so password-handling risks are not applicable today.
- **Status:** **Open**. **Severity:** Medium–High if exposed.
- **Minimal mitigation:** Introduce a single authentication mechanism for the course scope (e.g., token/login), store only password hashes, and protect all mutating and model-backed routes.

### A08 — Software and Data Integrity Failures

- **Locations:** uploaded PDFs are checked only by extension and `%PDF-` magic bytes (`app/main.py:297-318`), then parsed by PyMuPDF (`importer.py:21-30`); no SRI on `app.js` (`frontend/index.html:450`); no dependency hashes.
- **Assessment:** Potential. Malicious PDF handling depends on parser robustness; proposals are client-side but are revalidated by the normal endpoints on confirmation (`app/main.py:200-236`, `247-267`).
- **Status:** **Open**. **Severity:** Low–Medium.
- **Minimal mitigation:** Keep size/type checks, add a processing timeout, and pin/hash dependencies. SRI is unnecessary while assets are same-origin.

### A09 — Security Logging and Monitoring Failures

- **Locations:** no audit trail for card/comment mutations; unexpected assistant errors are converted to a generic 503 without logging (`app/main.py:371-385`); only model attempts are logged (`llm.py:67-83`, `135-142`).
- **Assessment:** Confirmed gap. Error responses do not leak internals, which is correct, but failures are not observable.
- **Status:** **Open**. **Severity:** Low–Medium.
- **Minimal mitigation:** Log mutations (action, card/comment ID, outcome) and use `logger.exception` for unexpected errors before returning 503. Never log keys or full request bodies.

### A10 — Server-Side Request Forgery (SSRF)

- **Locations:** no user-supplied URL is fetched anywhere. PRD bytes are written to a fixed filename inside a temporary directory (`app/main.py:320-322`); assistant tools search only in-memory board data (`assistant_service.py:201-241`); the LLM base URL is fixed (`llm.py:21`).
- **Assessment:** No exposure path found.
- **Status:** **Not applicable**. **Severity:** None.

---

## Existing protections (keep these intact)

- **Parameterized SQL** across `database.py`; counters and deletes are transactional (`database.py:113-141`, `235-253`).
- **Frontend output encoding** via `textContent`/`replaceChildren`; no HTML string interpolation of user data.
- **Server-side validation** with Pydantic: title 1–100, description ≤1000 (`app/models.py:33-36`, `44-48`), status enum and transition rules (`app/models.py:5-20`, `app/main.py:211-227`), assignee/comment checks (`app/models.py:23-30`, `66-69`).
- **Explicit assistant confirmation**: proposals are never persisted automatically (`assistant_service.py:404-427`); the UI requires Confirm/Cancel (`frontend/app.js:843-949`); confirmation calls the normal endpoints, which revalidate transitions, existence, and fields (`app/main.py:190-236`, `239-267`). On tool-budget exhaustion no proposal is returned (`assistant_service.py:445-451`).
- **Read-only assistant tools** for search; proposals are the only model-driven write path and require user action.
- **Upload controls**: 10 MB cap, extension and magic-byte checks, fixed temp filename (no path traversal) — `app/main.py:295-322`.
- **Secrets hygiene**: API keys only from environment (`llm.py:50,105`); `.env`, `cards.db`, and `.coverage` are git-ignored and untracked.
- **Error hygiene**: unexpected assistant failures return a generic 503 (`app/main.py:378-385`).

---

## Remediation plan (proposed, aligned with Days 18–21)

Nothing below is implemented yet. Each step requires approval and must preserve existing API behavior where the course spec does not change.

1. **Day 18 — Authentication:** add a user model and login/token issuance; hash passwords; load secrets/config from environment; protect all routes except health/login.
2. **Day 19 — Authorization:** add ownership (or role) checks to `GET/PATCH/DELETE /cards/{id}` and comment routes; return `404`/`403` consistently; add tests for cross-user access.
3. **Day 20 — Database migration:** introduce a `users` table and card ownership columns via a versioned migration script that preserves existing `cards.db` data and counters; keep IDs non-reused; document backup/rollback.
4. **Day 21 — Hardening and verification:** input bounds, rate limits on assistant/PRD, audit logging, `pip-audit` in CI, prompt-delimiting, and security regression tests (401/403, IDOR, oversized inputs). Confirm the suite and document residual risks.

Deferred / not applicable: SSRF controls, SQL-injection rewrites, and XSS escaping changes — current implementations are already safe.

---

## Status summary

| Category | Confirmed / Potential | Status | Severity |
|---|---|---|---|
| A01 Broken Access Control | Confirmed absence | Open | Medium–High (if exposed) |
| A02 Cryptographic Failures | Potential | Open | Low–Medium |
| A03 Injection (SQL/XSS) | — | Mitigated | — |
| A03 Prompt Injection | Confirmed exposure | Open | Medium |
| A04 Insecure Design | Confirmed missing bounds | Open | Medium |
| A05 Security Misconfiguration | Potential | Open | Low |
| A06 Vulnerable Components | Confirmed process gap | Open | Low–Medium |
| A07 Authentication Failures | Confirmed absence | Open | Medium–High (if exposed) |
| A08 Integrity Failures | Potential | Open | Low–Medium |
| A09 Logging/Monitoring | Confirmed gap | Open | Low–Medium |
| A10 SSRF | No path found | Not applicable | — |

Remaining open items are unresolved security risks, not fixed issues. No application files were modified while producing this document.
