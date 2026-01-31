#!/usr/bin/env python3
"""Quick test script for tool-based QA agent.

Run this to verify the tool-based architecture works with your Cursor API key.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.qa_agent import get_qa_agent
from app.config import get_settings


def main():
    """Test the tool-based QA agent."""
    print("=" * 70)
    print("Testing Tool-Based QA Agent")
    print("=" * 70)

    # Check configuration
    settings = get_settings()
    print(f"\nConfiguration:")
    print(f"  LLM Provider: {settings.llm_provider}")
    print(f"  Model: {settings.cursor_model if settings.llm_provider == 'cursor' else settings.openai_model}")
    print(f"  Docs Path: {settings.docs_repo_path}")

    # Check API key
    if settings.llm_provider == "cursor":
        if not settings.cursor_api_key:
            print("\n❌ ERROR: CURSOR_API_KEY not set in .env")
            sys.exit(1)
        print(f"  Cursor API Key: {'*' * 20}{settings.cursor_api_key[-10:]}")
    elif settings.llm_provider == "openai":
        if not settings.openai_api_key:
            print("\n❌ ERROR: OPENAI_API_KEY not set in .env")
            sys.exit(1)
        print(f"  OpenAI API Key: {'*' * 20}{settings.openai_api_key[-10:]}")

    # Initialize agent
    print("\n" + "=" * 70)
    print("Initializing QA Agent...")
    print("=" * 70)

    try:
        qa_agent = get_qa_agent()
        print(f"✅ Agent initialized successfully")
        print(f"   Client: {type(qa_agent.client).__name__}")
        print(f"   Model: {qa_agent.model}")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        sys.exit(1)

    # Ask a test question
    print("\n" + "=" * 70)
    print("Test Question")
    print("=" * 70)

    question = "What documentation files are available?"
    print(f"\nQuestion: {question}")
    print("\nCalling LLM with tools...")
    print("(This will use your API and may take 10-30 seconds)")

    try:
        result = qa_agent.answer(question, max_tool_iterations=5)

        print("\n" + "=" * 70)
        print("Result")
        print("=" * 70)

        print(f"\n📄 Answer:")
        print(f"{result['answer']}")

        print(f"\n🔧 Tools Used: {len(result['tool_calls'])}")
        for i, tool_call in enumerate(result['tool_calls'], 1):
            print(f"  {i}. {tool_call['tool']}({tool_call['arguments']})")
            if tool_call['result_preview']:
                preview = tool_call['result_preview'].replace('\n', ' ')[:100]
                print(f"     → {preview}...")

        print(f"\n📚 Sources: {len(result['sources'])}")
        for source in result['sources']:
            print(f"  - {source['source']}")

        print(f"\n⏱️  Performance:")
        print(f"  Total time: {result['processing_time']:.2f}s")
        print(f"  LLM time: {result['llm_duration']:.2f}s")
        print(f"  Tool time: {result['retrieval_time']:.2f}s")

        if result.get('tokens'):
            print(f"\n💰 Token Usage:")
            print(f"  Prompt: {result['tokens']['prompt']}")
            print(f"  Completion: {result['tokens']['completion']}")
            print(f"  Total: {result['tokens']['total']}")

        print("\n" + "=" * 70)
        print("✅ Test Completed Successfully!")
        print("=" * 70)

        print("\nThe tool-based QA agent is working!")
        print("It successfully:")
        print("  ✓ Called the Cursor/OpenAI API")
        print("  ✓ Used function calling with tools")
        print("  ✓ Explored documentation")
        print("  ✓ Generated an answer")

    except Exception as e:
        print(f"\n❌ Error during question answering:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
