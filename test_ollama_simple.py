#!/usr/bin/env python3
"""Simple test to check Ollama connection with OpenAI client."""

from openai import OpenAI

# Test Ollama connection
client = OpenAI(
    api_key="ollama",  # Dummy key
    base_url="http://localhost:11434/v1",
)

print("Testing Ollama connection...")
print(f"Base URL: {client.base_url}")

try:
    response = client.chat.completions.create(
        model="llama3.2:3b",
        messages=[
            {"role": "user", "content": "Say hello in one word"}
        ],
        max_tokens=10,
        timeout=30,
    )

    print("✅ Success!")
    print(f"Response: {response.choices[0].message.content}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
