
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
