# Claude Code Instructions for RepeatNoMore

## Project Overview

RepeatNoMore is an AI-powered framework assistant using RAG (Retrieval-Augmented Generation) with cloud LLM APIs. This document provides guidance for Claude Code when working on this project.

**Important:** Please read [_docs/DESIGN_DECISIONS.md](_docs/DESIGN_DECISIONS.md) for comprehensive architectural decisions, coding style preferences, and technical rationale.

## Project Structure

```
app/
├── main.py              # FastAPI application entry point
├── config.py            # Configuration management (Pydantic Settings)
├── rag/                 # RAG system components
│   ├── embeddings.py   # Sentence transformer embeddings
│   ├── vector_store.py # PostgreSQL/pgvector integration
│   ├── document_loader.py # Document loading and chunking
│   └── retriever.py    # Document retrieval logic
├── agents/             # AI agents
│   └── qa_agent.py     # Question-answering agent
├── api/                # REST API
│   ├── routes.py       # API endpoints
│   └── schemas.py      # Pydantic models
├── discord/            # Discord bot integration
│   ├── bot.py         # Main Discord bot class
│   ├── run.py         # Bot entry point
│   ├── embeds.py      # Discord embed builders
│   ├── utils.py       # Discord utilities
│   └── cogs/          # Command cogs
│       ├── workflow_cog.py  # Draft/question management
│       └── budget_cog.py    # Budget tracking commands
├── events/             # Event-driven system
│   ├── types.py       # Event type definitions
│   ├── dispatcher.py  # Event bus with pub/sub
│   ├── setup.py       # Handler registration
│   └── handlers/      # Event handlers
│       ├── mkdocs_handler.py      # MkDocs nav updates
│       ├── git_handler.py         # Git sync on events
│       └── notification_handler.py # Discord notifications
├── services/           # Business logic services
│   ├── workflow_service.py  # Draft/question workflow
│   ├── git_service.py       # Git operations (SSH/PAT)
│   └── qa_service.py        # QA processing
├── storage/            # Data persistence
│   ├── models.py      # Draft/Question models
│   └── repositories.py # JSON-based repositories
└── utils/              # Utilities
    ├── logging.py      # Structured logging
    └── security.py     # Security utilities
```

## Key Technologies

- **FastAPI**: Web framework and API
- **PostgreSQL + pgvector**: Vector database for embeddings
- **Cloud LLM APIs**: Anthropic (Claude), OpenAI, or local Ollama
- **LangChain**: Document loading and text splitting
- **sentence-transformers**: Local embedding generation
- **Pydantic**: Data validation and settings
- **Pytest**: Testing framework
- **Docker**: Service orchestration

## Development Guidelines

### Package Management

**Use `uv` for package management:**
```bash
# Install dependencies
uv pip install -r requirements.txt

# Add new package
uv pip install <package>

# Create virtual environment
uv venv
```

See [DESIGN_DECISIONS.md](_docs/DESIGN_DECISIONS.md#development-environment) for rationale.

### Code Style

- Follow PEP 8 style guide
- **Use comprehensive type hints** for all function signatures (see [DESIGN_DECISIONS.md](_docs/DESIGN_DECISIONS.md#type-hints))
- Write docstrings for all public functions (Google style)
- Use descriptive variable names
- Keep functions focused and small
- **Functional programming style is welcome** - use `functools`, comprehensions, immutability
- **Prefer composition over inheritance** - use protocols and dependency injection

### Testing

- Write unit tests for all new functionality
- Aim for >80% code coverage
- Use pytest fixtures for test setup
- Mock external services in unit tests
- Use integration tests for end-to-end flows

### Error Handling

- Use specific exception types
- Log errors with context using structlog
- Provide helpful error messages to users
- Handle edge cases gracefully
- Use try-except blocks judiciously

### Configuration

- All configuration via environment variables
- Use Pydantic Settings for type-safe config
- Never commit secrets or credentials
- Use `.env.example` as template

## Common Tasks

### Adding a New API Endpoint

1. Define request/response schemas in `app/api/schemas.py`
2. Add route handler in `app/api/routes.py`
3. Add logging for the endpoint
4. Write unit tests in `tests/unit/test_api.py`
5. Update API documentation

### Adding a New Agent

Existing agents:
- **QAAgent** (`app/agents/qa_agent.py`): Question answering with RAG
- **DraftSuggestionAgent** (`app/agents/draft_agent.py`): LLM-powered documentation change analysis

To add a new agent:
1. Create agent class in `app/agents/`
2. Implement initialization and core methods
3. Add integration with retriever/vector store
4. Write comprehensive tests
5. Document usage and examples

### Modifying RAG Components

1. Update the relevant module in `app/rag/`
2. Ensure backward compatibility if possible
3. Update tests to cover changes
4. Re-run integration tests
5. Update documentation if behavior changes

### Adding Documentation

1. Add markdown files to `knowledge_base/docs/`
2. Use clear headings and structure
3. Include code examples where relevant
4. Re-index after adding: `POST /api/index`

### Adding a Discord Command

1. Determine which cog the command belongs to:
   - **QACog** (`app/discord/bot.py`): Q&A commands (`/ask`, `/search`, `/help`)
   - **WorkflowCog** (`app/discord/cogs/workflow_cog.py`): Draft/question management
   - **BudgetCog** (`app/discord/cogs/budget_cog.py`): Budget tracking
2. Add the command using `@app_commands.command` decorator
3. For admin-only commands, add permission checks
4. Create embed responses using helpers in `app/discord/embeds.py`
5. Test locally with `DISCORD_GUILD_IDS` set for instant sync

Example command:
```python
@app_commands.command(name="my-command", description="Description here")
@app_commands.describe(param="Parameter description")
async def my_command(self, interaction: discord.Interaction, param: str) -> None:
    await interaction.response.defer(thinking=True)
    # ... process command
    await interaction.followup.send(embed=result_embed)
```

### Working with Events

The event system uses pub/sub pattern for decoupled architecture:

1. **Event Types** (`app/events/types.py`): Define new events here
2. **Emit Events**: Use the dispatcher in your service
   ```python
   from app.events import get_event_dispatcher, DocumentEvent, EventData

   dispatcher = get_event_dispatcher()
   await dispatcher.emit(DocumentEvent.DRAFT_APPROVED, EventData(
       draft_id="DRAFT-XXX",
       user_id="123",
       content="...",
   ))
   ```
3. **Handle Events**: Create handler in `app/events/handlers/`
   ```python
   class MyHandler:
       async def handle_event(self, event_type: DocumentEvent, data: EventData) -> None:
           if event_type == DocumentEvent.DRAFT_APPROVED:
               # Handle the event
               pass
   ```
4. **Register Handler**: Add to `app/events/setup.py`

Available events:
- `DRAFT_CREATED`, `DRAFT_APPROVED`, `DRAFT_REJECTED`
- `QUESTION_CREATED`, `QUESTION_ANSWERED`
- `DOC_CREATED`, `DOC_UPDATED`, `DOC_DELETED`
- `GIT_SYNC_REQUESTED`

## Testing Strategy

### Unit Tests

Located in `tests/unit/`, these test individual components:

```python
# Example unit test
def test_embed_text(generator):
    embedding = generator.embed_text("test")
    assert len(embedding) == generator.embedding_dimension
```

Run with: `pytest tests/unit/`

### Integration Tests

Located in `tests/integration/`, these test component interactions:

```python
# Example integration test
@pytest.mark.integration
def test_end_to_end_question_answering():
    # Test full pipeline
    pass
```

Run with: `pytest tests/integration/ -m integration`

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/unit/test_embeddings.py

# Specific test
pytest tests/unit/test_embeddings.py::TestEmbeddingGenerator::test_embed_text
```

## Docker Development

### Starting Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build app
```

### Accessing Containers

```bash
# App container
docker exec -it repeatnomore_app bash

# PostgreSQL
docker exec -it repeatnomore_postgres psql -U repeatnomore -d repeatnomore
```

## Debugging

### Enable Debug Logging

Set in `.env`:
```bash
LOG_LEVEL=DEBUG
```

### Common Issues

1. **PostgreSQL connection fails**
   - Check if container is running: `docker ps`
   - Check logs: `docker logs repeatnomore_postgres`
   - Verify port 5432 is not in use
   - Test connection: `docker exec -it repeatnomore_postgres pg_isready`

2. **pgvector extension not enabled**
   - Check extension: `docker exec -it repeatnomore_postgres psql -U repeatnomore -c "SELECT extname FROM pg_extension;"`
   - Enable manually: `CREATE EXTENSION IF NOT EXISTS vector;`

3. **API key missing or invalid**
   - Verify LLM_PROVIDER is set correctly in .env
   - Check that the corresponding API key is set (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)
   - Test API key validity with the provider's dashboard

### Logging

All components use structured logging:

```python
from app.utils.logging import get_logger

logger = get_logger(__name__)
logger.info("operation_completed", duration=1.5, items=10)
```

View logs:
```bash
docker-compose logs -f app
```

## API Development

### Testing API Locally

```bash
# Start server
uvicorn app.main:app --reload --port 8080

# Access docs
open http://localhost:8080/docs

# Test endpoint
curl -X POST http://localhost:8080/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I get started?"}'
```

### API Documentation

FastAPI auto-generates docs at `/docs` (Swagger UI) and `/redoc` (ReDoc).

## Performance Considerations

### Vector Store

- Batch document additions when possible
- Use appropriate chunk size (default: 1000)
- Consider chunk overlap for context (default: 200)
- Monitor vector store size

### Embeddings

- Cache embeddings when reusing queries
- Use batch processing for multiple documents
- Consider GPU acceleration for large batches

### LLM

- Adjust temperature for creativity vs consistency
- Limit max_tokens for faster responses
- Consider streaming for long responses (TODO)

## Security Best Practices

- Never commit `.env` file
- Rotate secrets regularly
- Validate all user inputs
- Sanitize inputs before LLM processing
- Use HTTPS in production
- Implement rate limiting
- Audit logging for sensitive operations

## Future Development

### Planned Features

1. **Streaming Responses**: Implement streaming for better UX
2. **Code Review Agent**: Analyze code and provide feedback
3. **Debug Agent**: Help troubleshoot errors
4. **Slack Integration**: Slack bot support
5. **Web Interface**: User-friendly web UI
6. **Teams Integration**: Microsoft Teams support (optional)

### Architecture Improvements

- Add response caching (Redis)
- Implement request queuing
- Add metrics and monitoring (Prometheus)
- Implement CI/CD pipeline
- Add backup and recovery procedures

## Contributing Workflow

1. Create feature branch: `git checkout -b feature/your-feature`
2. Implement changes with tests
3. Run quality checks:
   ```bash
   pytest
   ruff check app/
   mypy app/
   ```
4. Commit with descriptive messages
5. Push and create pull request
6. Address review feedback

## Useful Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Lint code
ruff check app/

# Format code
ruff format app/

# Type check
mypy app/

# Run server
uvicorn app.main:app --reload

# Docker rebuild
docker-compose up -d --build

# View logs
docker-compose logs -f app

# Access container
docker exec -it repeatnomore_app bash
```

## Contact and Support

For questions or issues:

- Check documentation in `knowledge_base/docs/`
- Review existing issues
- Create new issue with reproduction steps
- Include logs and error messages

## Notes for Claude Code

When working on this project:

1. **Always run tests** after making changes
2. **Check existing patterns** before adding new code
3. **Update tests** when modifying functionality
4. **Use type hints** for all new code
5. **Add logging** for important operations
6. **Handle errors gracefully** with helpful messages
7. **Document** complex logic with comments
8. **Keep it simple** - avoid over-engineering
9. **Test edge cases** - empty inputs, large inputs, etc.
10. **Review security** implications of changes
11. **📚 Update documentation** - See policy below

### 🔴 CRITICAL: Documentation Update Policy

**ALWAYS** update these documentation files when making significant changes:

1. **[knowledge_base/docs/architecture.md](knowledge_base/docs/architecture.md)**
   - Update when: Adding new components, changing data flow, modifying system architecture
   - Add to Feature Roadmap section for new features
   - Update component descriptions when modifying existing systems

2. **[_docs/DESIGN_DECISIONS.md](_docs/DESIGN_DECISIONS.md)**
   - Update when: Making architectural choices, choosing technologies, establishing patterns
   - Document the "why" behind decisions
   - Include alternatives considered and rationale

3. **[CLAUDE.md](CLAUDE.md)** (this file)
   - Update when: Adding new development workflows, common tasks, or guidelines
   - Keep project structure up-to-date

4. **[copilot-instructions.md](copilot-instructions.md)**
   - Update when: Establishing new code patterns, adding utilities, creating templates
   - Add code snippets for new patterns

### When to Update Documentation

✅ **Always Update:**
- New features or components
- New API endpoints
- New agent implementations
- Technology changes
- Architecture modifications

❌ **Usually Don't Update:**
- Minor bug fixes
- Typo corrections
- Small refactoring

Happy coding!
