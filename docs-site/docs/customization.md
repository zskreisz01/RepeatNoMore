---
sidebar_position: 4
---

# Customization

RepeatNoMore is designed to be forked and customized. Here's how to make it yours.

## Adding Your Documentation

### Knowledge Base Structure

```
knowledge_base/
├── docs/
│   ├── en/                 # English documentation
│   │   ├── getting_started.md
│   │   ├── architecture.md
│   │   └── troubleshooting.md
│   └── hu/                 # Hungarian (or your language)
│       └── getting_started.md
├── qa/
│   ├── accepted_qa_en.md   # Accepted Q&A pairs (English)
│   └── accepted_qa_hu.md   # Accepted Q&A pairs (Hungarian)
└── suggestions/
    └── suggested_features.md
```

### Indexing Your Docs

After adding/changing documentation:

```bash
curl -X POST http://localhost:8080/api/index
```

## Changing the LLM Provider

### Switch to OpenAI

```bash
# .env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4o
```

### Switch to Local Ollama

```bash
# .env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:70b
```

### Custom API Endpoint (Azure OpenAI, etc.)

```bash
# .env
LLM_PROVIDER=openai
OPENAI_API_KEY=your-azure-key
OPENAI_BASE_URL=https://your-resource.openai.azure.com/
OPENAI_MODEL=your-deployment-name
```

## Customizing Prompts

Edit the system prompts in `app/agents/qa_agent.py`:

```python
SYSTEM_PROMPT = """You are a helpful assistant for {your_company}.
You answer questions based on the provided documentation context.
Always be accurate and cite sources when possible.
If you don't know, say so clearly."""
```

## Multi-Language Support

RepeatNoMore supports multiple languages out of the box:

1. Add documentation in `knowledge_base/docs/{lang_code}/`
2. The bot automatically detects user language
3. Answers in the same language as the question

### Adding a New Language

1. Create folder: `knowledge_base/docs/de/` (for German)
2. Add translated documentation
3. Update `app/services/language_service.py`:

```python
SUPPORTED_LANGUAGES = ['en', 'hu', 'de']
```

## Extending the Bot

### Adding Custom Commands

In `app/discord/cogs/`:

```python
@app_commands.command(name="mycommand")
async def my_command(self, interaction: discord.Interaction):
    """Your custom command"""
    await interaction.response.send_message("Hello!")
```

### Adding API Endpoints

In `app/api/routes.py`:

```python
@router.post("/api/custom")
async def custom_endpoint(data: CustomSchema):
    # Your logic here
    return {"result": "success"}
```

## Deployment Customization

### Environment-Specific Configs

```bash
# Production
cp .env.example .env.production

# Staging  
cp .env.example .env.staging
```

### Docker Customization

Modify `docker-compose.yml` for your infrastructure:

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          memory: 4G
    environment:
      - WORKERS=4
```

## Contributing Back

Found a bug or made an improvement? Contributions welcome!

1. Fork the repository
2. Create a feature branch
3. Submit a Pull Request

See [CONTRIBUTING.md](https://github.com/zskreisz/RepeatNoMore/blob/main/CONTRIBUTING.md) for guidelines.
