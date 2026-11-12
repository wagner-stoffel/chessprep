# ChessPrep — Personalized chess match preparation

ChessPrep is an independent Streamlit application that compares publicly available Chess.com game histories and builds an evidence-based pre-match preparation plan. The interface is in Brazilian Portuguese.

> Independent project, not affiliated with or endorsed by Chess.com. Only the public read-only API is used. **Never use it to obtain assistance in an ongoing game.**

## Features

- Provide your Chess.com username and an opponent's username or profile URL.
- Fetch the latest 20, 50 or 100 completed standard-chess games from each player.
- Filter by rapid, blitz, bullet, daily or all time classes.
- Compare results by color, opening, and recent form.
- Show the opponent's most frequent responses to your usual opening moves.
- Find opening lines seen in both players' game histories.
- Generate distinct plans for playing White and Black and download a Markdown report.

The v0.1 recommendations are descriptive, deterministic, and backed by observed samples. ChessPrep **does not** detect blunders, run Stockfish or an LLM, or access private games. Future versions may add engine-backed analysis and interactive rehearsal.

## Run on Windows

Requires Python 3.11+ and Internet access. After cloning or downloading the repository, double-click `run_windows.bat`. Alternatively:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open http://localhost:8501. No Chess.com password or API key is required. Linux/macOS users can create a Python virtual environment and run `pip install -r requirements.txt && streamlit run app.py`.

## Technical structure

- `app.py` — Streamlit interface and orchestration.
- `chessprep/api.py` — username validation and sequential Chess.com PubAPI requests.
- `chessprep/analysis.py` — PGN parsing, player-perspective results, opening comparisons and report generation.
- `tests/` — offline unit tests for the API and analysis modules.
- `.github/workflows/tests.yml` — CI to compile and test with Python 3.11.

## Testing

```bash
python -m unittest discover -s tests -v
```

Live API integration could not be tested in the build environment; the app requires a local network connection to fetch games. The Chess.com PubAPI is documented at https://support.chess.com/en/articles/9650547-what-is-the-pubapi-and-how-do-i-use-it. Avoid parallel requests and account for API caching and rate limits.

## Roadmap

- Stockfish evaluation to identify recurring tactical mistakes.
- Opening trees and interactive position rehearsal.
- Evidence-grounded AI coaching and optional n8n scheduling.
- Optional Lichess import.

No open-source license is granted yet; select a license before inviting external reuse.
