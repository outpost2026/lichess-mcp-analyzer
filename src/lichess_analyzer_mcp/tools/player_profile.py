from lichess_analyzer_mcp.app import app
from lichess_analyzer_mcp.services.lichess_client import fetch_user_profile


@app.tool("lichess_player_profile")
async def lichess_player_profile(username: str):
    """Returns a player's Lichess profile, ratings, and stats.

    Args:
        username: Lichess username
    """
    try:
        profile = fetch_user_profile(username)
        perfs = profile.get("perfs", {})
        ratings = {}
        for variant in ("blitz", "rapid", "classical", "bullet", "correspondence"):
            if variant in perfs:
                ratings[variant] = {
                    "rating": perfs[variant].get("rating"),
                    "games": perfs[variant].get("games"),
                    "prog": perfs[variant].get("prog"),
                }
        return {
            "username": profile.get("username", username),
            "title": profile.get("title"),
            "ratings": ratings,
            "total_games": sum(p.get("games", 0) for p in perfs.values()),
            "created_at": profile.get("createdAt"),
            "seen_at": profile.get("seenAt"),
            "url": f"https://lichess.org/@/{username}",
        }
    except Exception as e:
        return {"error": str(e)}
