
# Cards API

A REST API for managing task cards, developed with FastAPI and Pydantic.

## Features

- Create new cards
- List existing cards
- Retrieve a card by ID
- Update card details and status
- Delete cards
- Validate incoming requests
- Enforce allowed status transitions
- Return appropriate HTTP error responses
- Configure CORS for the frontend

## Technologies

- Python 3.12
- FastAPI
- Pydantic v2
- Uvicorn

## Installation

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run the API

```bash
python -m uvicorn app.main:app --reload
```

Open the interactive API documentation:

http://127.0.0.1:8000/docs

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| GET | /cards | List cards |
| POST | /cards | Create a card |
| GET | /cards/{card_id} | Retrieve a card |
| PATCH | /cards/{card_id} | Update a card |
| DELETE | /cards/{card_id} | Delete a card |

## HTTP Status Codes

- 200: Successful request
- 201: Card created
- 204: Card deleted
- 404: Card not found
- 409: Illegal status transition
- 422: Invalid request data

## Storage

Cards are currently stored in memory.

Data will be lost when the server restarts.

## Project Status

Day 8: Initial Cards API implementation.
Day 9: Automated API tests with pytest (planned).

## API Usage Examples

### Create a Card

Send a POST request to `/cards` with the following JSON body:

```json
{
  "title": "Implement API tests",
  "description": "Write automated tests using pytest"
}
```

A successful request returns HTTP 201 with a generated card ID and the initial status `spec`.

### Retrieve Cards

Use `GET /cards` to retrieve all existing cards.

Use `GET /cards/{card_id}` to retrieve a specific card.

### Update a Card

Send a PATCH request to `/cards/{card_id}`:

```json
{
  "status": "ready"
}
```

Status changes must follow the allowed workflow. Invalid transitions return HTTP 409 Conflict.

### Delete a Card

Send a DELETE request to `/cards/{card_id}`.

A successful deletion returns HTTP 204 No Content.

### Interactive Documentation

All endpoints can be explored and tested using Swagger UI:

http://127.0.0.1:8000/docs


## Automated Testing (Day 9)

The Cards API includes automated tests using pytest
and FastAPI TestClient.

### Test Coverage

- Total automated tests: 16
- Tests passed: 16
- Code coverage: 100%
- Testing framework: pytest
- Coverage tool: coverage.py

### Tested Features

- Root and health check endpoints
- Creating and listing cards
- Retrieving individual cards
- Updating card information and status
- Deleting cards
- Handling nonexistent cards (404)
- Rejecting illegal status transitions (409)
- Validating invalid input (422)
- Complete card status workflow
- Rejecting null and invalid status values

### Running Tests

Install project dependencies:

```bash
python -m pip install -r requirements.txt
```

Run all automated tests:

```bash
python -m pytest tests/test_cards.py -v
```

Run tests with coverage:

```bash
python -m coverage run --source=app -m pytest tests/test_cards.py -v
python -m coverage report -m
```

### Test Isolation

An automatic pytest fixture resets the in-memory
card storage before each test to prevent tests
from interfering with each other.
