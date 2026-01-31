"""Entry point for running the Discord bot as a standalone service."""

import asyncio
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.discord.bot import run_discord_bot
from app.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)


def main() -> None:
    """Main entry point."""
    setup_logging()
    logger.info("starting_discord_bot_service")

    try:
        asyncio.run(run_discord_bot())
    except KeyboardInterrupt:
        logger.info("discord_bot_stopped_by_user")
    except Exception as e:
        logger.error("discord_bot_failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
