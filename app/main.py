from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from app.models import (
    ALLOWED_TRANSITIONS,
    CardCreate,
    CardRead,
    CardStatus,
    CardUpdate,
    CommentCreate,
    CommentRead,
)
from fastapi.middleware.cors import CORSMiddleware

import tempfile
from pathlib import Path

from fastapi import File, UploadFile
from starlette.concurrency import run_in_threadpool

import database
from prd_service import generate_prd_breakdown
from schemas import Breakdown

from pydantic import BaseModel
from assistant_service import answer_board_request


@asynccontextmanager
async def lifespan(_app):
    initialize_storage()
    yield


app = FastAPI(
    title="Cards API",
    description="A REST API for managing cards",
    version="1.0.0",
    lifespan=lifespan,
)



app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)


# Temporary in-memory storage
comments: dict[int, CommentRead] = {}
next_comment_id = 1

# Aliases for compatibility with different storage naming conventions
card_comments = comments
comment_store = comments
comments_store = comments


class _CardsDict(dict):
    def clear(self):
        super().clear()
        comments.clear()
        global next_comment_id
        next_comment_id = 1


cards: _CardsDict = _CardsDict()
next_card_id = 1


def reload_storage_from_db():
    """Replace the in-memory cache with persisted cards and comments."""

    global next_card_id, next_comment_id

    stored_cards = database.load_cards()
    stored_comments = database.load_comments()

    cards.clear()
    comments.clear()

    for row in stored_cards:
        card = CardRead.model_validate(row)
        cards[card.id] = card

    for row in stored_comments:
        comment = CommentRead.model_validate(row)
        comments[comment.id] = comment

    next_card_id, next_comment_id = database.get_next_ids()


def initialize_storage():
    """Create the database if needed and hydrate the in-memory cache."""

    database.initialize_database()
    reload_storage_from_db()


@app.get("/")
async def root():
    return {"message": "Cards API is running"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post(
    "/cards",
    response_model=CardRead,
    status_code=status.HTTP_201_CREATED
)
async def create_card(card: CardCreate):
    global next_card_id

    new_card = CardRead(
        id=next_card_id,
        title=card.title,
        description=card.description,
        status=CardStatus.SPEC,
        assignee=card.assignee
    )

    database.create_card(new_card.model_dump(mode="json"))
    cards[next_card_id] = new_card
    next_card_id += 1

    return new_card

@app.get("/cards", response_model=list[CardRead])
async def list_cards():
    return list(cards.values())



@app.get(
    "/cards/{card_id}",
    response_model=CardRead,
    responses={
        404: {"description": "Card not found"}
    }
)

async def read_card(card_id: int):
    if card_id not in cards:
        raise HTTPException(
            status_code=404,
            detail="Card not found"
        )

    return cards[card_id]

@app.delete(
    "/cards/{card_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "Card not found"}
    }
)
async def delete_card(card_id: int):
    if card_id not in cards:
        raise HTTPException(
            status_code=404,
            detail="Card not found"
        )

    # Remove the card and its comments from SQLite first so a failed
    # database write cannot leave the in-memory cache out of sync.
    database.delete_card(card_id)

    # Clean up comments associated with the deleted card
    to_delete = [comment_id for comment_id, comment in comments.items() if comment.card_id == card_id]
    for comment_id in to_delete:
        del comments[comment_id]

    del cards[card_id]
    return None


@app.patch(
    "/cards/{card_id}",
    response_model=CardRead,
    responses={
        404: {"description": "Card not found"},
        409: {"description": "Illegal card status transition"},
        422: {"description": "Invalid request data"}
    }
)

async def update_card(card_id: int, update: CardUpdate):
    if card_id not in cards:
        raise HTTPException(
            status_code=404,
            detail="Card not found"
        )

    current_card = cards[card_id]

    changes = update.model_dump(exclude_unset=True)

    if "status" in changes:
        new_status = changes["status"]

        if new_status is None:
            raise HTTPException(
                status_code=422,
                detail="Status cannot be null"
            )

        if new_status != current_card.status:
            allowed = ALLOWED_TRANSITIONS[current_card.status]

            if new_status not in allowed:
                raise HTTPException(
                    status_code=409,
                    detail="Illegal card status transition"
                )

    if "title" in changes and changes["title"] is None:
        raise HTTPException(
            status_code=422,
            detail="Title cannot be null"
        )

    if "description" in changes and changes["description"] is None:
        raise HTTPException(
            status_code=422,
            detail="Description cannot be null"
        )

    updated_data = current_card.model_dump()
    updated_data.update(changes)

    updated_card = CardRead.model_validate(updated_data)
    database.save_card(updated_card.model_dump(mode="json"))
    cards[card_id] = updated_card

    return updated_card


@app.post(
    "/cards/{card_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Card not found"}
    }
)
async def create_comment(card_id: int, comment: CommentCreate):
    global next_comment_id

    if card_id not in cards:
        raise HTTPException(
            status_code=404,
            detail="Card not found"
        )

    new_comment = CommentRead(
        id=next_comment_id,
        card_id=card_id,
        author=comment.author,
        text=comment.text
    )

    database.create_comment(new_comment.model_dump(mode="json"))
    comments[next_comment_id] = new_comment
    next_comment_id += 1

    return new_comment


@app.get(
    "/cards/{card_id}/comments",
    response_model=list[CommentRead],
    responses={
        404: {"description": "Card not found"}
    }
)
async def list_comments(card_id: int):
    if card_id not in cards:
        raise HTTPException(
            status_code=404,
            detail="Card not found"
        )

    return [comment for comment in comments.values() if comment.card_id == card_id]



@app.post("/prd/preview", response_model=Breakdown)
async def preview_prd(
    file: UploadFile = File(...),
    use_ocr: bool = False,
):
    """Upload a PDF and generate draft cards without saving them."""

    max_file_size = 10 * 1024 * 1024  # 10 MB

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a PDF file."
        )

    try:
        content = await file.read(max_file_size + 1)
    finally:
        await file.close()

    if len(content) > max_file_size:
        raise HTTPException(
            status_code=413,
            detail="PDF is too large. Maximum size is 10 MB."
        )

    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file."
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_path = Path(temp_dir) / "uploaded.pdf"
        pdf_path.write_bytes(content)

        try:
            
            breakdown = await run_in_threadpool(
                generate_prd_breakdown,
                str(pdf_path),
                use_ocr,
                existing_cards=[
                    card.model_dump()
                    for card in cards.values()
                ],
            )

        except ValueError as error:
            raise HTTPException(
                status_code=422,
                detail=str(error)
            ) from error

    return breakdown


class AssistantMessage(BaseModel):
    message: str


class AssistantReply(BaseModel):
    reply: str
    proposal: dict | None = None


@app.post(
    "/assistant/chat",
    response_model=AssistantReply,
    response_model_exclude_none=True,
)
async def assistant_chat(request: AssistantMessage):
    if not request.message.strip():
        raise HTTPException(
            status_code=422,
            detail="Message cannot be empty",
        )

    current_cards = [
        card.model_dump(mode="json")
        for card in cards.values()
    ]

    try:
        reply, proposal = await run_in_threadpool(
            answer_board_request,
            request.message,
            current_cards,
        )

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "The assistant is temporarily unavailable. "
                "Please try again."
            ),
        ) from error

    return AssistantReply(reply=reply, proposal=proposal)

