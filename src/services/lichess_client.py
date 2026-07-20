"""Lichess API client wrapper using berserk."""

import os
from typing import Optional
import berserk

_token: Optional[str] = None
_client: Optional[berserk.Client] = None


def get_token() -> Optional[str]:
    global _token
    if _token is None:
        _token = os.environ.get("LICHESS_TOKEN")
    return _token


def get_client() -> berserk.Client:
    global _client
    if _client is None:
        token = get_token()
        if token:
            session = berserk.TokenSession(token)
            _client = berserk.Client(session)
        else:
            _client = berserk.Client()
    return _client


def fetch_user_profile(username: str) -> dict:
    client = get_client()
    return client.users.get(username)


def fetch_user_games(username: str, max_games: int = 10) -> list[dict]:
    client = get_client()
    games = []
    for game in client.games.export_by_player(username, max=max_games):
        games.append(game)
    return games


def fetch_game_pgn(game_id: str) -> str:
    client = get_client()
    return client.games.export(game_id, as_pgn=True)


def fetch_cloud_eval(fen: str) -> Optional[dict]:
    client = get_client()
    try:
        return client.analysis.get_cloud_evaluation(fen)
    except Exception as e:
        import logging

        logging.getLogger("lichess-mcp.lichess_client").warning("cloud_eval failed: %s", e)
        return None


def fetch_opening_explorer(fen: str, source: str = "lichess") -> dict:
    import httpx

    if source == "masters":
        url = f"https://explorer.lichess.ovh/masters?fen={fen}"
    else:
        url = f"https://explorer.lichess.ovh/lichess?fen={fen}"
    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()
