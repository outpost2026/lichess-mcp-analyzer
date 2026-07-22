"""Lichess API client wrapper using berserk."""

import json
import os
import time
from typing import Optional

import berserk
import httpx

_token: Optional[str] = None
_client: Optional[berserk.Client] = None

PGN_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "pgn_cache")
GAMES_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "game_cache")
USER_GAMES_TTL = 3600  # 1 hour


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


def _pgn_cache_path(game_id: str) -> str:
    return os.path.join(PGN_CACHE_DIR, f"{game_id}.pgn")


def _load_pgn_cache(game_id: str) -> Optional[str]:
    path = _pgn_cache_path(game_id)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def _save_pgn_cache(game_id: str, pgn: str) -> None:
    os.makedirs(PGN_CACHE_DIR, exist_ok=True)
    path = _pgn_cache_path(game_id)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(pgn)
        os.replace(tmp, path)
    except OSError:
        pass


def _user_games_cache_path(username: str) -> str:
    return os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "data", "game_cache", f"{username}_games.json"
    )


def _load_user_games_cache(username: str) -> Optional[list[dict]]:
    path = _user_games_cache_path(username)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cached_time = data.get("_cached_at", 0)
        if time.time() - cached_time > USER_GAMES_TTL:
            return None
        return data.get("games", [])
    except (OSError, json.JSONDecodeError):
        return None


def _save_user_games_cache(username: str, games: list[dict]) -> None:
    path = _user_games_cache_path(username)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                {"_cached_at": time.time(), "games": games}, f, ensure_ascii=False, default=str
            )
        os.replace(tmp, path)
    except OSError:
        pass


def fetch_user_profile(username: str) -> dict:
    client = get_client()
    data = client.users.get_by_id(username)
    if isinstance(data, list) and len(data) > 0:
        return data[0]
    return data


def _json_safe(obj):
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return obj


_USER_GAMES_ENDPOINTS = [
    "/api/games/user/{username}",  # original berserk endpoint (OpenAPI-documented)
    "/games/export/{username}",  # replacement in lila routes (master branch)
    "/api/user/{username}/games",  # alternative path in some client libs
]


def _export_by_player(username: str, max_games: int = 10) -> list[dict]:
    """Fetch user games, trying multiple known Lichess endpoints.

    As of 2026-07, all known endpoints return 404 on production.
    Per-game export via fetch_game_pgn(game_id) still works.
    """
    token = get_token()
    headers = {"Accept": "application/x-ndjson"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    params = {"max": max_games}
    last_error = None
    for path_tpl in _USER_GAMES_ENDPOINTS:
        path = path_tpl.format(username=username)
        url = f"https://lichess.org{path}"
        try:
            with httpx.Client() as client:
                response = client.get(url, headers=headers, params=params, timeout=15)
                if response.status_code == 200:
                    games = []
                    for line in response.iter_lines():
                        line = line.strip()
                        if line:
                            games.append(json.loads(line))
                    return games
                last_error = f"{response.status_code} {url}"
        except Exception as e:
            last_error = f"{e} {url}"
    raise RuntimeError(
        f"Nepodařilo se stáhnout hry uživatele '{username}' — "
        f"Lichess API endpoint pro výpis her uživatele je na produkci nedostupný "
        f"(všechny známé endpointy vrací 404). "
        f"Per-game export přes fetch_game_pgn(game_id) stále funguje. "
        f"Poslední pokus: {last_error}"
    )


def fetch_user_games(username: str, max_games: int = 10) -> list[dict]:
    cached = _load_user_games_cache(username)
    if cached is not None:
        return cached[:max_games]
    games = _export_by_player(username, max_games=max_games)
    games = [_json_safe(g) for g in games]
    _save_user_games_cache(username, games)
    return games


def fetch_game_pgn(game_id: str) -> str:
    cached = _load_pgn_cache(game_id)
    if cached is not None:
        return cached
    client = get_client()
    pgn = client.games.export(game_id, as_pgn=True)
    _save_pgn_cache(game_id, pgn)
    return pgn


def fetch_cloud_eval(fen: str) -> Optional[dict]:
    client = get_client()
    try:
        return client.analysis.get_cloud_evaluation(fen)
    except Exception as e:
        import logging

        logging.getLogger("lichess-mcp.lichess_client").warning("cloud_eval failed: %s", e)
        return None


def fetch_opening_explorer(fen: str, source: str = "lichess") -> dict:
    client = get_client()
    if source == "masters":
        return client.opening_explorer.get_masters_games(position=fen)  # type: ignore
    return client.opening_explorer.get_lichess_games(position=fen)  # type: ignore
