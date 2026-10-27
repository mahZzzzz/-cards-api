from fastapi import FastAPI, HTTPException, status
from app.models import CardCreate, CardRead, CardStatus, CardUpdate
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Cards API",
    description="A REST API for managing cards",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


# Temporary in-memory storage
cards: dict[int, CardRead] = {}
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
        status=CardStatus.SPEC
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

