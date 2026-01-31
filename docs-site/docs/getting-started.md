---
sidebar_position: 1
---

# Getting Started

Get RepeatNoMore running in 5 minutes with Docker Compose or UV.

## Prerequisites

- **Docker & Docker Compose** (recommended) OR **Python 3.11+** with UV
- **16GB RAM** minimum (32GB recommended)
- **LLM API Key**: Anthropic Claude or OpenAI (or local Ollama)
- **Discord Bot Token** (optional, for Discord integration)

## Quick Start with Docker

### 1. Clone the Repository

```bash
git clone https://github.com/zskreisz/RepeatNoMore
cd RepeatNoMore
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# Required: Choose your LLM provider
LLM_PROVIDER=anthropic  # or 'openai' or 'ollama'

# For Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# For OpenAI
# OPENAI_API_KEY=sk-your-key-here
# OPENAI_MODEL=gpt-4o

# Optional: Discord Bot
DISCORD_TOKEN=your-bot-token
DISCORD_GUILD_ID=your-server-id
```

### 3. Start Services

```bash
docker-compose up -d
```

### 4. Index Your Documentation

```bash
curl -X POST http://localhost:8080/api/index
```

### 5. Test It

```bash
curl -X POST http://localhost:8080/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I get started?"}'
```

## Quick Start with UV

### 1. Clone and Setup

```bash
git clone https://github.com/zskreisz/RepeatNoMore
cd RepeatNoMore
```

### 2. Install Dependencies

```bash
uv sync --extra dev
```

### 3. Start Supporting Services

```bash
docker-compose -f docker-compose.services.yml up -d
```

### 4. Configure and Run

```bash
cp .env.example .env
# Edit .env with your settings

uv run uvicorn app.main:app --reload --port 8080
```

## Deployment Options

| Option | Best For | Cost | Setup Time |
|--------|----------|------|------------|
| **Cloud API** (Anthropic/OpenAI) | Quick start, small teams | $40-200/mo | 1 day |
| **Azure + Local LLM** | Compliance requirements | $500-1500/mo | 1-2 weeks |
| **Self-hosted** | Full control, large scale | Hardware + $500/mo | 2-4 weeks |

## Next Steps

- [Architecture Overview](./architecture) — Understand how RepeatNoMore works
- [Discord Setup](./discord-setup) — Configure the Discord bot
- [Customization](./customization) — Adapt it to your needs
