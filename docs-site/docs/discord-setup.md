---
sidebar_position: 3
---

# Discord Setup

Configure RepeatNoMore as a Discord bot for your server.

## Creating the Bot

### 1. Create a Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Name it "RepeatNoMore" (or your preferred name)
4. Go to "Bot" section
5. Click "Add Bot"

### 2. Configure Bot Permissions

Enable these **Privileged Gateway Intents**:
- ✅ Message Content Intent
- ✅ Server Members Intent (optional, for user info)

### 3. Get Your Token

1. In the Bot section, click "Reset Token"
2. Copy the token — you'll only see it once!
3. Add it to your `.env`:

```bash
DISCORD_TOKEN=your-bot-token-here
```

### 4. Invite the Bot

1. Go to OAuth2 → URL Generator
2. Select scopes: `bot`, `applications.commands`
3. Select permissions:
   - Read Messages/View Channels
   - Send Messages
   - Embed Links
   - Attach Files
   - Read Message History
   - Use Slash Commands
4. Copy the generated URL and open it in browser
5. Select your server and authorize

### 5. Configure Guild ID

Get your server (guild) ID:
1. Enable Developer Mode in Discord settings
2. Right-click your server → Copy Server ID
3. Add to `.env`:

```bash
DISCORD_GUILD_ID=your-server-id
```

## Available Commands

| Command | Description |
|---------|-------------|
| `/ask <question>` | Ask a question about your documentation |
| `/search <query>` | Search the knowledge base |
| `/draft-suggest` | Propose a documentation update |
| `/accept` | Accept and save a Q&A pair |
| `/reject` | Reject a proposed answer |
| `/list-drafts` | View pending documentation drafts |
| `/list-questions` | View escalated questions |

## Channel Configuration

Optionally configure dedicated channels:

```bash
# In .env
DISCORD_DRAFTS_CHANNEL=drafts-review
DISCORD_QUESTIONS_CHANNEL=escalated-questions
```

These channels receive notifications for:
- New draft submissions
- Escalated questions that need admin attention

## Testing

After setup, test in your Discord:

```
/ask How do I get started with RepeatNoMore?
```

You should get an AI-generated response based on your indexed documentation.
