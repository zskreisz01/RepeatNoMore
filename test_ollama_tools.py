#!/usr/bin/env python3
"""Test Ollama with function calling."""

from openai import OpenAI

# Test Ollama with tools
client = OpenAI(
    api_key="ollama",
    base_url="http://localhost:11434/v1",
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"}
                },
                "required": ["location"]
            }
        }
    }
]

print("Testing Ollama with function calling...")

try:
    response = client.chat.completions.create(
        model="llama3.2:3b",
        messages=[
            {"role": "user", "content": "What's the weather in Paris?"}
        ],
        tools=tools,
        tool_choice="auto",
        max_tokens=200,
        timeout=30,
    )

    message = response.choices[0].message
    print(f"✅ Success!")
    print(f"Finish reason: {response.choices[0].finish_reason}")

    if message.tool_calls:
        print(f"Tool calls: {len(message.tool_calls)}")
        for tool_call in message.tool_calls:
            print(f"  - {tool_call.function.name}({tool_call.function.arguments})")
    else:
        print("No tool calls made")
        print(f"Response: {message.content}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
