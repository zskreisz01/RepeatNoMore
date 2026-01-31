# Getting Started with RepeatNoMore Framework

## Introduction

Welcome to the RepeatNoMore Framework! This guide will help you get started with using our AI-powered assistant for framework development and support.

## What is RepeatNoMore?

RepeatNoMore is an intelligent framework assistant that helps developers by:

- Answering framework-related questions using RAG (Retrieval-Augmented Generation)
- Providing code review and suggestions
- Debugging assistance
- Configuration validation
- Interactive learning sessions

## Quick Start

### Prerequisites

Before using RepeatNoMore, ensure you have:

1. Python 3.11 or higher
2. Docker and Docker Compose installed
3. At least 16GB RAM (32GB recommended)
4. 50GB free disk space for models and data

### Installation Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-org/repeatnomore.git
   cd repeatnomore
   ```

2. **Set Up Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start the Services**
   ```bash
   docker-compose up -d
   ```

4. **Wait for Models to Download**
   The first startup will download the required models. This may take 10-15 minutes.

5. **Verify Installation**
   ```bash
   curl http://localhost:8080/api/health
   ```

## Using RepeatNoMore in Teams

### Adding the Bot

1. Go to your Teams workspace
2. Click on "Apps" in the left sidebar
3. Search for "RepeatNoMore"
4. Click "Add" to install the bot

### Asking Questions

Simply @mention the bot in any channel:

```
@RepeatNoMore How do I configure authentication in the framework?
```

The bot will respond with relevant documentation and examples.

## Common Use Cases

### 1. Framework Questions
Ask any question about the framework's features, APIs, or best practices.

**Example:**
```
@RepeatNoMore What's the recommended way to handle database connections?
```

### 2. Code Review
Share code snippets for review and suggestions.

**Example:**
```
@RepeatNoMore Can you review this code?
[code snippet]
```

### 3. Debugging Help
Get help troubleshooting errors and issues.

**Example:**
```
@RepeatNoMore I'm getting error "Connection timeout" - what could cause this?
```

### 4. Configuration Validation
Validate your configuration files.

**Example:**
```
@RepeatNoMore Check this configuration:
[config snippet]
```

## Tips for Best Results

1. **Be Specific**: The more context you provide, the better the answer
2. **Include Error Messages**: When debugging, include the full error message
3. **Provide Code Context**: When asking about code, include relevant surrounding code
4. **Use Keywords**: Include framework-specific terms to get more accurate results

## Next Steps

- Read the [Framework Architecture Guide](./architecture.md)
- Learn about [Configuration Options](./configuration.md)
- Explore [Best Practices](./best_practices.md)
- Check out [Troubleshooting Guide](./troubleshooting.md)

## Getting Help

If you encounter issues:

1. Check the [FAQ](./faq.md)
2. Review [Common Errors](./common_errors.md)
3. Ask the bot: `@RepeatNoMore help`
4. Contact support: support@repeatnomore.example.com
