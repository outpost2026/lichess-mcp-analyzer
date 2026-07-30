"""Lichess API client wrapper using berserk."""

import json
import os
import re
import time
from typing import Optional

import berserk

_token: Optional[str] = None
_client: Optional[berserk.Client] = None

PGN_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "pgn_cache")
GAMES_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "game_cache")
USER_GAMES_TTL = 3600  # 1 hour


def get_token() -> Optional[str]:
    global _token
    if _token is None:
        _token = os.environ.get("LICHESS_TOKEN")
    if _token is None:
        _dotenv = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
        if os.path.isfile(_dotenv):
            with open(_dotenv, encoding="utf-8-sig") as _f:
                for _line in _f:
                    _line = _line.strip()
                    if _line.startswith("LICHESS_TOKEN="):
                        _token = _line.split("=", 1)[1].strip()
                        os.environ["LICHESS_TOKEN"] = _token
                        break
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


def _sanitize_id(raw: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "", raw)


def _pgn_cache_path(game_id: str) -> str:
    return os.path.join(PGN_CACHE_DIR, f"{_sanitize_id(game_id)}.pgn")


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
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "data",
        "game_cache",
        f"{_sanitize_id(username)}_games.json",
    )


def _games_index_path(username: str) -> str:
    return os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "data",
        "game_cache",
        f"{_sanitize_id(username)}_index.json",
    )


def _build_games_index(games: list[dict], username: str) -> dict:
    by_result = {"win": [], "loss": [], "draw": []}
    summary = []
    for g in games:
        gid = g.get("id", "")
        res = _game_result_for_player(g, username) or ""
        players = g.get("players", {})
        white = players.get("white", {})
        black = players.get("black", {})
        white_name = white.get("user", {}).get("name", "") or ""
        black_name = black.get("user", {}).get("name", "") or ""
        if res in by_result:
            by_result[res].append(gid)
        opening_data = g.get("opening", {})
        opening_name = opening_data.get("name", "") if isinstance(opening_data, dict) else ""
        summary.append(
            {
                "id": gid,
                "result": res,
                "date": str(g.get("createdAt", "")),
                "opening": opening_name,
                "opponent": black_name if white_name.lower() == username.lower() else white_name,
                "opponent_rating": (
                    black.get("rating")
                    if white_name.lower() == username.lower()
                    else white.get("rating")
                )
                or 0,
                "color": "white" if white_name.lower() == username.lower() else "black",
                "status": g.get("status", ""),
            }
        )
    return {
        "_cached_at": time.time(),
        "total": len(games),
        "by_result": by_result,
        "games": summary,
    }


def _load_games_index(username: str) -> Optional[dict]:
    path = _games_index_path(username)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if time.time() - data.get("_cached_at", 0) > USER_GAMES_TTL:
            return None
        return data
    except (OSError, json.JSONDecodeError):
        return None


def _save_games_index(username: str, index: dict) -> None:
    path = _games_index_path(username)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, default=str)
        os.replace(tmp, path)
    except OSError:
        pass


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


def _export_by_player(username: str, max_games: int = 999) -> list[dict]:
    """Fetch user games via berserk export_by_player with retry on 429.

    Berserk 0.14+ handles internal pagination; we just pass max and
    collect results.  Lichess API returns up to ~100 games per call,
    and berserk's iterator may yield more via its own pagination.
    """
    client = get_client()
    for attempt in range(3):
        try:
            page = list(
                client.games.export_by_player(
                    username=username,
                    max=max_games,
                    as_pgn=False,
                    opening=True,
                    evals=True,
                )
            )
            return page[:max_games]
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate limit" in err_str.lower():
                wait = 2 ** (attempt + 1)
                print(
                    f"[lichess_client] Rate limited, retry in {wait}s",
                    file=__import__("sys").stderr,
                )
                time.sleep(wait)
                continue
            if "404" in err_str or "not found" in err_str.lower():
                return []
            raise
    return []


def _game_result_for_player(game: dict, username: str) -> str | None:
    """Return 'win', 'loss', or 'draw' for the given player in a game."""
    winner = game.get("winner")
    if winner is None:
        return "draw"
    white_name = game.get("players", {}).get("white", {}).get("user", {}).get("name", "") or ""
    black_name = game.get("players", {}).get("black", {}).get("user", {}).get("name", "") or ""
    player_is_white = white_name.lower() == username.lower()
    player_won = (winner == "white" and player_is_white) or (
        winner == "black" and not player_is_white
    )
    return "win" if player_won else "loss"


def fetch_user_games(username: str, max_games: int = 10, result: str = "all") -> list[dict]:
    cached = _load_user_games_cache(username)
    index = _load_games_index(username) if result != "all" and cached is not None else None
    if cached is not None:
        if result == "all":
            return cached[:max_games]
        if index is not None:
            gids = set(index.get("by_result", {}).get(result, []))
            filtered = [g for g in cached if g.get("id", "") in gids]
        else:
            filtered = [g for g in cached if _game_result_for_player(g, username) == result]
        return filtered[:max_games]
    games = _export_by_player(username, max_games=max_games)
    games = [_json_safe(g) for g in games]
    _save_user_games_cache(username, games)
    _save_games_index(username, _build_games_index(games, username))
    if result == "all":
        return games[:max_games]
    filtered = [g for g in games if _game_result_for_player(g, username) == result]
    return filtered[:max_games]


def fetch_user_games_metadata(username: str) -> Optional[dict]:
    index = _load_games_index(username)
    if index is not None:
        return {k: v for k, v in index.items() if k != "games"}
    cached = _load_user_games_cache(username)
    if cached is None:
        return None
    index = _build_games_index(cached, username)
    _save_games_index(username, index)
    return {k: v for k, v in index.items() if k != "games"}


def _game_id_from_created_at(raw: str) -> str:
    """Extract clean game ID from a berserk-style dict or timestamp string."""
    return raw if isinstance(raw, str) and len(raw) == 8 else ""


def fetch_game_by_id(game_id: str) -> Optional[dict]:
    """Fetch a single game as raw API dict (as_pgn=False) with retry."""
    client = get_client()
    for attempt in range(3):
        try:
            raw = client.games.export(game_id, as_pgn=False)
            if isinstance(raw, dict):
                return raw
            return None
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate limit" in err_str.lower():
                wait = 2 ** (attempt + 1)
                print(
                    f"[lichess_client] Rate limited fetch_game_by_id, retry in {wait}s",
                    file=__import__("sys").stderr,
                )
                time.sleep(wait)
                continue
            if "404" in err_str or "not found" in err_str.lower():
                return None
            raise
    return None


def update_games_index_with_game(username: str, game_id: str) -> None:
    """After single-game analysis, add/update the game in the user index.

    Fetches raw game data from the API and inserts into both
    Systeq_games.json (the games list) and Systeq_index.json (the index).
    """
    raw = fetch_game_by_id(game_id)
    if raw is None:
        return

    # 1) Update Systeq_games.json — append or replace
    games_path = _user_games_cache_path(username)
    existing_games: list[dict] = []
    if os.path.isfile(games_path):
        try:
            with open(games_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            existing_games = data.get("games", [])
        except (OSError, json.JSONDecodeError):
            existing_games = []

    # Replace if already present, else append
    found = False
    for i, g in enumerate(existing_games):
        if g.get("id") == game_id:
            existing_games[i] = raw
            found = True
            break
    if not found:
        existing_games.insert(0, raw)  # newest first

    _save_user_games_cache(username, existing_games)

    # 2) Rebuild and save index from the updated list
    index = _build_games_index(existing_games, username)
    _save_games_index(username, index)


def get_pending_analysis(username: str, depth: int = 0) -> list[str]:
    """Return game IDs with no per-game analysis cache at exact depth.

    Compares game IDs in username_games.json against per-game cache files
    in data/game_cache/.  Uses exact depth match — game analyzed at d=14
    is still pending for a d=12 request.
    """
    if depth == 0:
        from lichess_analyzer_mcp.config.depth import DEPTH_DEFAULTS

        depth = DEPTH_DEFAULTS["batch"]["pending"]
    import glob

    cached_games = _load_user_games_cache(username)
    if cached_games is None:
        return []

    pending = []
    for g in cached_games:
        gid = g.get("id", "")
        if not gid:
            continue
        color = "white"
        white_name = g.get("players", {}).get("white", {}).get("user", {}).get("name", "") or ""
        if white_name.lower() == username.lower():
            color = "white"
        else:
            color = "black"
        pattern = os.path.join(GAMES_CACHE_DIR, f"{gid}_{color}_d{depth}.json")
        if not glob.glob(pattern):
            pending.append(gid)
    return pending


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
