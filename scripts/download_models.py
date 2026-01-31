#!/usr/bin/env python3
"""
Model download script for RepeatNoMore.

NOTE: This script is now a no-op since we switched to API-based embeddings.
No local models need to be downloaded during build time.

Embeddings are now generated using OpenAI-compatible APIs (OpenAI or Cursor)
which are accessed at runtime via API keys.
"""

import sys

def main():
    """No-op: API-based embeddings don't require model downloads."""
    print("=" * 60)
    print("RepeatNoMore Model Setup")
    print("=" * 60)
    print("ℹ️  Using API-based embeddings (OpenAI/Cursor)")
    print("ℹ️  No local models need to be downloaded")
    print("ℹ️  Ensure OPENAI_API_KEY or CURSOR_API_KEY is set in .env")
    print("=" * 60)
    print("✓ Setup complete")
    sys.exit(0)

if __name__ == "__main__":
    main()
