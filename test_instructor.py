
import os

import instructor
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()


class TestCard(BaseModel):
    title: str
    goal: str


client = instructor.from_openai(
    OpenAI(
        api_key=os.environ["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1",
        timeout=90.0,
    ),
    mode=instructor.Mode.JSON,
)

card = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    response_model=TestCard,
    max_retries=2,
    messages=[
        {
            "role": "user",
            "content": (
                "Create one task card for implementing "
                "a login page. Return a JSON object."
            ),
        }
    ],
    temperature=0,
)

print("VALIDATION SUCCESSFUL!")
print(card.model_dump_json(indent=2))
