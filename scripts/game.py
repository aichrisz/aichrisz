#!/usr/bin/env python3
"""Night Audit game: guess which room (101-106) hides Moin's spare key today.

Env: ISSUE_NUMBER, ISSUE_AUTHOR, ISSUE_BODY, TODAY (YYYY-MM-DD, UTC, optional).
- Computes today's secret room deterministically from the date.
- Parses the player's guess from the issue body (one guess per player per day).
- Updates game/leaderboard.json and renders it into README.md (GAME markers).
- Writes the reply comment to comment.md and the close decision to should_close.txt.
"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone

ROOMS = [101, 102, 103, 104, 105, 106]
GAME_START = "<!-- GAME:START -->"
GAME_END = "<!-- GAME:END -->"


def today_utc():
    return os.environ.get("TODAY") or datetime.now(timezone.utc).strftime("%Y-%m-%d")


def secret_room(date_str):
    h = hashlib.sha256(f"moin-key-{date_str}".encode()).hexdigest()
    return 101 + int(h, 16) % 6


def parse_guess(body):
    m = re.search(r"### Which room hides the key\?\s*\n+\s*(\d{3})", body or "")
    if m and int(m.group(1)) in ROOMS:
        return int(m.group(1))
    for n in re.findall(r"\b(10[1-6])\b", body or ""):
        return int(n)
    return None


def load_board():
    try:
        with open("game/leaderboard.json", encoding="utf-8") as f:
            data = json.load(f)
            data.setdefault("players", {})
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"players": {}}


def save_board(board):
    os.makedirs("game", exist_ok=True)
    with open("game/leaderboard.json", "w", encoding="utf-8") as f:
        json.dump(board, f, indent=2, sort_keys=True)
        f.write("\n")


def render_board_md(board):
    players = board.get("players", {})
    ranked = sorted(
        ((l, p) for l, p in players.items() if p.get("points", 0) > 0),
        key=lambda kv: (-kv[1].get("points", 0), kv[0]),
    )
    if not ranked:
        return "_No one has found the key yet. Be the first!_"
    medals = ["🥇", "🥈", "🥉"]
    lines = ["| Player | Points |", "| --- | --- |"]
    for i, (login, p) in enumerate(ranked[:10]):
        prefix = medals[i] + " " if i < 3 else ""
        lines.append(f"| {prefix}@{login} | {p.get('points', 0)} |")
    return "\n".join(lines)


def update_readme(board_md):
    with open("README.md", encoding="utf-8") as f:
        text = f.read()
    if GAME_START not in text or GAME_END not in text:
        raise SystemExit("GAME markers not found in README.md")
    pattern = re.compile(re.escape(GAME_START) + r".*?" + re.escape(GAME_END), re.DOTALL)
    new = f"{GAME_START}\n{board_md}\n{GAME_END}"
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(pattern.sub(new, text, count=1))


def write_comment(text, close):
    with open("comment.md", "w", encoding="utf-8") as f:
        f.write(text + "\n")
    with open("should_close.txt", "w", encoding="utf-8") as f:
        f.write("yes" if close else "no")


def main():
    author = os.environ["ISSUE_AUTHOR"]
    body = os.environ.get("ISSUE_BODY", "")
    date_str = today_utc()
    secret = secret_room(date_str)
    guess = parse_guess(body)
    board = load_board()
    player = board["players"].get(author, {"points": 0, "last_played": None})

    if guess is None:
        write_comment(
            f"@{author} Hmm, I couldn't read your guess. "
            "Pick a room (101-106) from the dropdown and open a fresh issue! 🗝️",
            close=True,
        )
        return

    if player.get("last_played") == date_str:
        write_comment(
            f"@{author} You already tried your luck today. "
            "The night audit continues tomorrow! 🌙",
            close=True,
        )
        return

    player["last_played"] = date_str
    if guess == secret:
        player["points"] = player.get("points", 0) + 1
        board["players"][author] = player
        save_board(board)
        update_readme(render_board_md(board))
        write_comment(
            f"🎉 DING DING DING! @{author} found Moin's key in room **{secret}**! "
            f"That's 1 point for you (total: {player['points']}). "
            "The front desk thanks you. 🗝️",
            close=True,
        )
    else:
        board["players"][author] = player
        save_board(board)
        update_readme(render_board_md(board))
        direction = "higher" if secret > guess else "lower"
        write_comment(
            f"@{author} Not in room **{guess}**. "
            f"The key is hiding in a **{direction}**-numbered room. 🔍\n\n"
            "One guess per day, see you tomorrow!",
            close=True,
        )


if __name__ == "__main__":
    main()
