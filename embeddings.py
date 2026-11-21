
from functools import lru_cache

from sentence_transformers import SentenceTransformer, util


MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def get_embedding_model():
    """Load the multilingual embedding model only once."""
    return SentenceTransformer(MODEL_NAME)


def similar_cards(
    text: str,
    existing_cards: list[dict],
    threshold: float = 0.50,
) -> list[dict]:
    """
    Find existing cards semantically similar to a new card.

    Returns matches sorted by cosine similarity.
    """

    if not text.strip() or not existing_cards:
        return []

    model = get_embedding_model()

    titles = [
        card["title"]
        for card in existing_cards
    ]

    embeddings = model.encode(
        [text] + titles,
        convert_to_tensor=True,
        normalize_embeddings=True,
    )

    query_embedding = embeddings[0]
    card_embeddings = embeddings[1:]

    similarities = util.cos_sim(
        query_embedding,
        card_embeddings,
    )[0]

    matches = []

    for card, score in zip(existing_cards, similarities):
        similarity = float(score)

        if similarity >= threshold:
            matches.append({
                "id": card.get("id"),
                "title": card["title"],
                "similarity": round(similarity, 4),
            })

    return sorted(
        matches,
        key=lambda item: item["similarity"],
        reverse=True,
    )
