"""Deterministic, evidence-based comparisons of completed chess games."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from io import StringIO
from urllib.parse import unquote, urlparse

import chess.pgn


def parse_games(games: list[dict], username: str) -> list[dict]:
    """Parse published PGNs; skip malformed games instead of guessing moves."""
    user = username.casefold()
    parsed = []
    for raw in games:
        white = raw.get("white", {})
        black = raw.get("black", {})
        white_user = white.get("username", "").casefold()
        black_user = black.get("username", "").casefold()
        if user not in (white_user, black_user):
            continue
        try:
            game = chess.pgn.read_game(StringIO(raw["pgn"]))
            if game is None or game.errors:
                continue
            board = game.board()
            moves = []
            for move in game.mainline_moves():
                moves.append(board.san(move))
                board.push(move)
                if len(moves) >= 20:
                    break
        except (ValueError, KeyError, TypeError):
            continue
        if not moves:
            continue
        color = "white" if white_user == user else "black"
        player = white if color == "white" else black
        opponent = black if color == "white" else white
        if player.get("result") == "win":
            outcome = "Vitória"
        elif opponent.get("result") == "win":
            outcome = "Derrota"
        else:
            outcome = "Empate"
        eco_url = game.headers.get("ECOUrl", "")
        opening_from_url = unquote(urlparse(eco_url).path.split("/")[-1]).replace("-", " ")
        opening = game.headers.get("Opening") or opening_from_url or "Não identificada"
        end_time = int(raw.get("end_time", 0))
        parsed.append({
            "color": color,
            "outcome": outcome,
            "moves": tuple(moves),
            "opening": opening,
            "eco": game.headers.get("ECO", ""),
            "time_class": raw.get("time_class", "unknown"),
            "date": datetime.fromtimestamp(end_time, tz=timezone.utc).strftime("%Y-%m-%d") if end_time else "—",
            "url": raw.get("url", ""),
            "rating": player.get("rating"),
            "opponent_rating": opponent.get("rating"),
        })
    return parsed


def summary(games: list[dict], color: str | None = None) -> dict:
    selected = [g for g in games if color is None or g["color"] == color]
    counts = Counter(g["outcome"] for g in selected)
    n = len(selected)
    return {
        "total": n,
        "wins": counts["Vitória"],
        "draws": counts["Empate"],
        "losses": counts["Derrota"],
        "score_pct": round(100 * (counts["Vitória"] + 0.5 * counts["Empate"]) / n, 1) if n else None,
    }


def top_openings(games: list[dict], color: str, n: int = 8) -> list[dict]:
    selected = [g for g in games if g["color"] == color]
    by_opening: dict[str, list[dict]] = {}
    for g in selected:
        label = (g["eco"] + " · " if g["eco"] else "") + g["opening"]
        by_opening.setdefault(label, []).append(g)
    result = [{"Abertura": label, "Partidas": len(items), "Pontuação (%)": summary(items)["score_pct"]}
              for label, items in by_opening.items()]
    return sorted(result, key=lambda x: (-x["Partidas"], x["Abertura"]))[:n]


def frequency(games: list[dict], color: str, index: int, prefix: tuple[str, ...] = ()) -> tuple[Counter, int]:
    """Count SAN moves at given ply, conditioned on earlier exact moves."""
    selected = [g for g in games if g["color"] == color and
                len(g["moves"]) > index and g["moves"][:len(prefix)] == prefix]
    return Counter(g["moves"][index] for g in selected), len(selected)


def format_moves(moves: tuple[str, ...] | list[str]) -> str:
    parts = []
    for i, move in enumerate(moves):
        if i % 2 == 0:
            parts.append(f"{i // 2 + 1}. {move}")
        else:
            parts.append(move)
    return " ".join(parts)


def common_paths(your_games: list[dict], opp_games: list[dict], your_color: str,
                 max_plies: int = 8, top: int = 5) -> list[dict]:
    other_color = "black" if your_color == "white" else "white"
    yours = [g for g in your_games if g["color"] == your_color]
    theirs = [g for g in opp_games if g["color"] == other_color]
    if not yours or not theirs:
        return []
    counter_y: Counter = Counter()
    counter_t: Counter = Counter()
    for games, counter in [(yours, counter_y), (theirs, counter_t)]:
        for g in games:
            for k in range(2, min(max_plies, len(g["moves"])) + 1):
                counter[g["moves"][:k]] += 1
    overlap = []
    for seq in counter_y.keys() & counter_t.keys():
        count_y, count_t = counter_y[seq], counter_t[seq]
        overlap.append({
            "Linha": format_moves(seq),
            "Lances": len(seq),
            "Suas partidas": count_y,
            "Partidas do adversário": count_t,
            "_weight": min(count_y / len(yours), count_t / len(theirs)),
        })
    # Prefer the most recurrent matching paths while keeping depth informative.
    overlap.sort(key=lambda row: (-row["_weight"] * row["Lances"]**0.5,
                                  -row["Lances"], -min(row["Suas partidas"], row["Partidas do adversário"])))
    result = []
    for row in overlap:
        if any(row["Linha"] == existing["Linha"] for existing in result):
            continue
        result.append({key: value for key, value in row.items() if not key.startswith("_")})
        if len(result) >= top:
            break
    return result


def build_plan(your_games: list[dict], opp_games: list[dict], your_color: str) -> list[str]:
    notes = []
    if your_color == "white":
        your_first, your_n = frequency(your_games, "white", 0)
        if not your_first:
            notes.append("Seu histórico de brancas é insuficiente para selecionar uma primeira jogada com base no repertório.")
            return notes
        first, count = your_first.most_common(1)[0]
        notes.append(f"Seu primeiro lance mais habitual é 1. {first} ({count}/{your_n} partidas de brancas). É um ponto de partida, não uma recomendação de motor.")
        replies, relevant = frequency(opp_games, "black", 1, (first,))
        if replies:
            options = ", ".join(f"1... {san} ({num}/{relevant})" for san, num in replies.most_common(3))
            notes.append(f"Contra 1. {first}, o adversário respondeu {options}. Prepare principalmente as respostas mais frequentes.")
        else:
            notes.append(f"Não há partidas suficientes do adversário de pretas contra 1. {first}. Não é possível prever sua resposta com segurança.")
        notes.append("Revise os primeiros 6 a 8 lances das linhas coincidentes e pratique os planos depois do desenvolvimento.")
    else:
        opp_first, opp_n = frequency(opp_games, "white", 0)
        if not opp_first:
            notes.append("O histórico do adversário de brancas é insuficiente para antecipar sua primeira jogada.")
            return notes
        first, count = opp_first.most_common(1)[0]
        notes.append(f"De brancas, o adversário começou com 1. {first} em {count}/{opp_n} partidas. Treine primeiro essa estrutura.")
        your_replies, relevant = frequency(your_games, "black", 1, (first,))
        if your_replies:
            options = ", ".join(f"1... {san} ({num}/{relevant})" for san, num in your_replies.most_common(3))
            notes.append(f"Contra 1. {first}, suas respostas anteriores foram {options}. Comece por uma que você já conhece e avalie-a posteriormente com o motor.")
        else:
            notes.append(f"Você não tem partidas suficientes de pretas contra 1. {first}. Monte e treine uma resposta sólida antes do confronto.")
        notes.append("Treine o desenvolvimento até o roque, incluindo a posição que costuma surgir após o quarto lance.")
    sample = min(len(your_games), len(opp_games))
    if sample < 10:
        notes.append("Atenção: uma das amostras tem menos de 10 partidas. As frequências são exploratórias e não preveem com confiança a próxima partida.")
    notes.append("Antes do jogo, resolva exercícios de tática e examine partidas perdidas nessas linhas. Não utilize sugestões externas durante a partida.")
    return notes


def to_markdown(your_user: str, opp_user: str, your_games: list[dict], opp_games: list[dict]) -> str:
    lines = ["# ChessPrep — Relatório pré-partida", "", f"Jogador: **{your_user}**", f"Adversário: **{opp_user}**", "",
             f"Amostras analisadas: {len(your_games)} partidas suas e {len(opp_games)} do adversário.",
             "", "Estatísticas descritivas, não avaliação técnica de um motor de xadrez.", ""]
    for color, label in [("white", "Jogando de brancas"), ("black", "Jogando de pretas")]:
        lines.extend([f"## {label}", ""])
        lines.extend(f"- {item}" for item in build_plan(your_games, opp_games, color))
        lines.append("")
        paths = common_paths(your_games, opp_games, color)
        if paths:
            lines.extend(["Linhas presentes nos dois históricos:", ""])
            for path in paths:
                lines.append(f"- {path['Linha']} — você: {path['Suas partidas']}, adversário: {path['Partidas do adversário']}")
            lines.append("")
    lines.append("Fonte: partidas públicas da Chess.com PubAPI. Projeto independente, sem afiliação ao Chess.com.")
    return "\n".join(lines)
