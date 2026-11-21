
import os
import logging

from llm import chat_completion

# Show which model is being used
logging.basicConfig(level=logging.INFO)

# Simulate a failed primary model
# This change affects only this Python process
os.environ["GROQ_MODELS"] = (
    "invalid-model-for-testing,"
    "openai/gpt-oss-20b"
)

messages = [
    {
        "role": "user",
        "content": "Reply with exactly: Fallback works"
    }
]

response = chat_completion(
    messages=messages,
    temperature=0,
    max_completion_tokens=100,
)

print("\nModel used:", response.model)
print("Response:", response.choices[0].message.content)
