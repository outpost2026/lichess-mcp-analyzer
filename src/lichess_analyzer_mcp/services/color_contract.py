"""Single colour contract for every layer.

`white` and `black` are colours. `both` is a CLI mode that makes two calls with
explicit colours; it is never a valid colour value. Unknown values raise
`InvalidColorError` instead of silently becoming black in the analysis and
white in the compact metadata (the pre-2026-11-13 behaviour).

Decision: D6 / D6a in `docs/AUDIT_INTEGRATION_2026-11-13.md`.
"""

from __future__ import annotations

VALID_COLORS: tuple[str, ...] = ("white", "black")


class InvalidColorError(ValueError):
    """A colour outside the contract (`white` | `black`)."""

    code = "INVALID_COLOR"

    def __init__(self, value: object) -> None:
        super().__init__(
            f"invalid color {value!r}; expected 'white' or 'black' "
            "('both' is a CLI mode: call once per colour)"
        )
        self.value = value


class ColorUndetectedError(ValueError):
    """The player colour could not be resolved and none was given explicitly."""

    code = "COLOR_UNDETECTED"

    def __init__(self, game_id: str = "", username: str = "", *, reason: str = "") -> None:
        if not reason:
            reason = (
                f"could not detect colour of {username!r} in game {game_id!r}; "
                "pass color='white' or color='black' explicitly"
            )
        super().__init__(reason)
        self.game_id = game_id
        self.username = username


def normalize_color(value: str | None, *, allow_empty: bool = False) -> str:
    """Return a contract colour, or `""` when empty is allowed.

    Raises `InvalidColorError` for anything else, including `both`.
    """
    if value is None or str(value).strip() == "":
        if allow_empty:
            return ""
        raise InvalidColorError(value)
    normalized = str(value).strip().lower()
    if normalized in VALID_COLORS:
        return normalized
    raise InvalidColorError(value)
