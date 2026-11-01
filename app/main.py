from fastapi import FastAPI, HTTPException, status
from app.models import CardCreate, CardRead, CardStatus, CardUpdate, CommentCreate, CommentRead
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Cards API",
    description="A REST API for managing cards",
    version="1.0.0"
)



app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
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

    # Clean up comments associated with the deleted card
    to_delete = [comment_id for comment_id, comment in comments.items() if comment.card_id == card_id]
    for comment_id in to_delete:
        del comments[comment_id]

    del cards[card_id]
    return None


ALLOWED_TRANSITIONS = {
    CardStatus.SPEC: {CardStatus.READY},
    CardStatus.READY: {CardStatus.IN_PROGRESS},
    CardStatus.IN_PROGRESS: {CardStatus.REVIEW},
    CardStatus.REVIEW: {CardStatus.DONE},
    CardStatus.DONE: set(),
}



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

    updated_data = current_card.model_dump()
    updated_data.update(changes)

    updated_card = CardRead.model_validate(updated_data)
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
