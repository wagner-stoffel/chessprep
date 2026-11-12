"""Chess.com PubAPI client. Only documented public endpoints are used."""
from __future__ import annotations

import os
import re
from urllib.parse import urlparse
import requests

API_BASE = "https://api.chess.com/pub/player"
USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,50}$")


class ChessAPIError(Exception):
    """An actionable error when reading public Chess.com data."""


def parse_username(value: str) -> str:
    """Accept a Chess.com member URL or a plain username; reject arbitrary URLs."""
    value = value.strip()
    if not value:
        raise ValueError("Informe o nome de usuário ou o link do perfil.")
    if "://" in value or value.lower().startswith(("www.", "chess.com/")):
        url = value if "://" in value else "https://" + value
        parts = urlparse(url)
        if parts.scheme != "https" or parts.netloc.lower() not in {"www.chess.com", "chess.com"}:
            raise ValueError("Use um link HTTPS válido de chess.com/member/usuario.")
        segments = [s for s in parts.path.split("/") if s]
        if len(segments) != 2 or segments[0].lower() not in {"member", "players"}:
            raise ValueError("Use um link de perfil Chess.com (/member/usuario).")
        value = segments[1]
    if not USERNAME_RE.fullmatch(value):
        raise ValueError("Nome de usuário Chess.com inválido.")
    return value.lower()


def get_recent_games(username: str, limit: int = 50, time_class: str = "all") -> list[dict]:
    """Retrieve completed standard-chess games, scanning archives newest first.

    HTTP access is sequential (Chess.com asks callers to avoid parallel requests).
    """
    username = parse_username(username)
    if not (1 <= limit <= 500):
        raise ValueError("O limite de partidas deve ficar entre 1 e 500.")
    if time_class not in {"all", "rapid", "blitz", "bullet", "daily"}:
        raise ValueError("Modalidade inválida.")
    contact = os.getenv("CHESSPREP_CONTACT", "github.com")
    session = requests.Session()
    session.headers.update({
        "User-Agent": f"ChessPrep/0.1 (standalone study app; contact: {contact})",
        "Accept": "application/json",
    })

    def load(url: str) -> dict:
        try:
            response = session.get(url, timeout=18)
            if response.status_code == 429:
                raise ChessAPIError("O Chess.com limitou temporariamente as consultas. Tente novamente mais tarde.")
            if response.status_code == 404:
                raise ChessAPIError(f"Perfil ou arquivo não encontrado: {username}.")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise ChessAPIError(f"Não foi possível acessar a API pública do Chess.com: {exc}") from exc
        except ValueError as exc:
            raise ChessAPIError("A API retornou uma resposta que não é JSON válido.") from exc

    try:
        archives = load(f"{API_BASE}/{username}/games/archives").get("archives", [])
        collected: list[dict] = []
        for archived_url in reversed(archives):
            # Construct our own URL from the archive's YYYY/MM suffix; never fetch arbitrary hosts.
            match = re.search(r"/games/(\d{4})/(\d{2})/?$", archived_url)
            if not match:
                continue
            year, month = match.groups()
            if not (1 <= int(month) <= 12):
                continue
            monthly = load(f"{API_BASE}/{username}/games/{year}/{month}").get("games", [])
            for game in monthly:
                if game.get("rules", "chess") != "chess" or not game.get("pgn"):
                    continue
                if time_class != "all" and game.get("time_class") != time_class:
                    continue
                collected.append(game)
            if len(collected) >= limit:
                break
        collected.sort(key=lambda g: g.get("end_time", 0), reverse=True)
        return collected[:limit]
    finally:
        session.close()
