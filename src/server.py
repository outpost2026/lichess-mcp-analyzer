import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

from src.tools.fetch_games import register_fetch_games
from src.tools.analyze_game import register_analyze_game
from src.tools.analyze_position import register_analyze_position
from src.tools.opening_explorer import register_opening_explorer
from src.tools.player_profile import register_player_profile
from src.tools.diagnose_player import register_diagnose_player
from src.tools.match_patterns import register_match_patterns

server = Server("lichess-analyzer")


def register_all_tools(srv):
    register_fetch_games(srv)
    register_analyze_game(srv)
    register_analyze_position(srv)
    register_opening_explorer(srv)
    register_player_profile(srv)
    register_diagnose_player(srv)
    register_match_patterns(srv)


register_all_tools(server)


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="lichess-analyzer",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
