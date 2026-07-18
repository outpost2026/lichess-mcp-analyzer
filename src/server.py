import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.app import app

# Tool imports trigger @app.tool() decorator registration
from src.tools import fetch_games
from src.tools import analyze_game
from src.tools import analyze_position
from src.tools import opening_explorer
from src.tools import player_profile
from src.tools import diagnose_player
from src.tools import match_patterns


async def main():
    await app.run()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
