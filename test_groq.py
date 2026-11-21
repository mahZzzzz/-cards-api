
import os
import json

from dotenv import load_dotenv
from groq import Groq
from schemas import Breakdown

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise RuntimeError("GROQ_API_KEY is missing")

client = Groq(api_key=api_key, timeout=30.0)

prd_text = """
Section 2.1 - User Authentication

Users must be able to log in using their
email address and password.

Invalid login attempts must display
an appropriate error message.
"""

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {
            "role": "system",
            "content": """
You are a PRD breakdown assistant.

Convert the provided PRD into small,
independently testable draft cards.

Return a JSON object with:
- cards: a list of cards
- ambiguities: a list of strings

Every card must contain:
- title
- goal
- acceptance_criteria (list of strings)
- dependencies (list of strings)
- prd_section
- possible_duplicate (boolean)

Use only requirements supported by the PRD.
Return only valid JSON.
"""
        },
        {
            "role": "user",
            "content": prd_text
        }
    ],
    response_format={"type": "json_object"},
    temperature=0
)

raw_result = json.loads(
    response.choices[0].message.content
)

breakdown = Breakdown.model_validate(raw_result)

print("VALIDATION SUCCESSFUL!")
print(
    json.dumps(
        breakdown.model_dump(),
        indent=2,
        ensure_ascii=False
    )
)
