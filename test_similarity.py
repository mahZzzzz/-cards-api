
from embeddings import similar_cards

existing_cards = [
    {
        "id": 1,
        "title": "Create a user login page",
    },
    {
        "id": 2,
        "title": "Add comments to cards",
    },
    {
        "id": 3,
        "title": "Implement task search",
    },
    {
        "id": 4,
        "title": "ساخت صفحه ورود کاربران",
    },
]

new_title = "Create a user login page"

matches = similar_cards(
    text=new_title,
    existing_cards=existing_cards,
    threshold=0.0,
)

print("\nSimilarity ranking:")

for match in matches:
    print(
        f"{match['similarity']:.4f} | "
        f"ID: {match['id']} | "
        f"{match['title']}"
    )
