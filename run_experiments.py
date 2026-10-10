"""Reproducible, seat-balanced comparisons of named Coup policies."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from datetime import date
from math import sqrt
from pathlib import Path

from coup_simulator import Game

CANDIDATES = (
    "baseline", "income", "foreign_aid", "taxer", "captain", "assassin",
    "exchange", "bluff_heavy", "challenge_low", "challenge_heavy",
    "block_aggressive",
)
FIELDS = ("honest", "bluffing", "skeptical", "mixed")
FIELD_POLICY = {
    "honest": ("baseline",),
    "bluffing": ("bluff_heavy",),
    "skeptical": ("challenge_heavy",),
    "mixed": ("baseline", "bluff_heavy", "challenge_heavy"),
}
BASE_SEED = 20261010
RAW_COLUMNS = ("players", "field", "policy", "seat", "game", "seed", "winner", "won", "draw", "turns")
SUMMARY_COLUMNS = ("players", "field", "policy", "wins", "draws", "games", "win_rate", "lower95", "upper95", "mean_turns")
SEAT_COLUMNS = ("players", "field", "policy", "seat", "wins", "draws", "games", "win_rate", "lower95", "upper95")


def game_seed(players: int, field: str, seat: int, game: int, panel: int = 0) -> int:
    """Same initial seed panel for every focal policy; disjoint field/seat panels."""
    return BASE_SEED + panel * 1_000_000_000 + players * 100_000_000 + FIELDS.index(field) * 10_000_000 + seat * 1_000_000 + game


def roster(players: int, policy: str, field: str, seat: int, game: int) -> list[str]:
    opponents = list((FIELD_POLICY[field] * players)[:players - 1])
    if field == "mixed":
        options = FIELD_POLICY[field]
        opponents = [options[(game + j) % len(options)] for j in range(players - 1)]
    names = [policy] + opponents
    return names[-seat:] + names[:-seat] if seat else names


def wilson(wins: int, games: int) -> tuple[float, float]:
    if games == 0:
        return (0.0, 1.0)
    p = wins / games
    z = 1.96
    denom = 1 + z * z / games
    center = (p + z * z / (2 * games)) / denom
    half = z * sqrt(p * (1 - p) / games + z * z / (4 * games * games)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def _row(players: int, field: str, policy: str, wins: int, draws: int, games: int, turns: int, seat=None) -> dict:
    low, high = wilson(wins, games)
    row = {
        "players": players, "field": field, "policy": policy,
        "wins": wins, "draws": draws, "games": games,
        "win_rate": round(wins / games, 6),
        "lower95": round(low, 6), "upper95": round(high, 6),
    }
    if seat is None:
        row["mean_turns"] = round(turns / games, 2)
    else:
        row["seat"] = seat
    return row


def run_study(output_dir: Path, games_per_seat: int = 200, players=(2, 3, 4, 5, 6),
              fields=FIELDS, candidates=CANDIDATES, panel: int = 0) -> tuple[list[dict], list[dict]]:
    if games_per_seat < 1 or games_per_seat >= 1_000_000:
        raise ValueError("games_per_seat must be between 1 and 999999")
    if any(n < 2 or n > 6 for n in players):
        raise ValueError("players must be between 2 and 6")
    if any(field not in FIELDS for field in fields):
        raise ValueError("unknown field")
    if any(policy not in CANDIDATES for policy in candidates):
        raise ValueError("unknown candidate")
    if panel < 0:
        raise ValueError("panel must be nonnegative")
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "games.csv"
    summary = []
    seats = []
    with raw_path.open("w", newline="") as raw_file:
        writer = csv.DictWriter(raw_file, fieldnames=RAW_COLUMNS)
        writer.writeheader()
        for n in players:
            for field in fields:
                for policy in candidates:
                    total_wins = total_draws = total_turns = 0
                    for seat in range(n):
                        seat_wins = seat_draws = seat_turns = 0
                        for game in range(games_per_seat):
                            seed = game_seed(n, field, seat, game, panel)
                            names = roster(n, policy, field, seat, game)
                            assert names[seat] == policy
                            trial = Game(n, seed, names)
                            winner = trial.run()
                            won = winner == seat
                            draw = winner is None
                            seat_wins += won
                            seat_draws += draw
                            seat_turns += trial.turn
                            writer.writerow({
                                "players": n, "field": field, "policy": policy,
                                "seat": seat, "game": game, "seed": seed,
                                "winner": "" if draw else winner,
                                "won": int(won), "draw": int(draw), "turns": trial.turn,
                            })
                        total_wins += seat_wins
                        total_draws += seat_draws
                        total_turns += seat_turns
                        seats.append(_row(n, field, policy, seat_wins, seat_draws,
                                          games_per_seat, seat_turns, seat))
                    summary.append(_row(n, field, policy, total_wins, total_draws,
                                        n * games_per_seat, total_turns))
    summary.sort(key=lambda row: (row["players"], row["field"], -row["win_rate"], row["policy"]))
    seats.sort(key=lambda row: (row["players"], row["field"], row["policy"], row["seat"]))
    for filename, columns, rows in (
        ("results.csv", SUMMARY_COLUMNS, summary),
        ("benchmark_results.csv", SEAT_COLUMNS, seats),
    ):
        with (output_dir / filename).open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    checksums = {}
    for name in ("coup_simulator.py", "run_experiments.py", "test_coup_simulator.py",
                 "games.csv", "results.csv", "benchmark_results.csv"):
        path = (Path(__file__).parent if name.endswith(".py") else output_dir) / name
        checksums[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {
        "date": date.today().isoformat(),
        "rules_profile": "standard base Coup, two-player first seat starts with one coin",
        "rulebook": "https://www.qugs.org/rules/r131357.pdf",
        "python": platform.python_version(),
        "players": list(players),
        "fields": list(fields),
        "candidates": list(candidates),
        "games_per_seat": games_per_seat,
        "panel": panel,
        "seed_formula": "20261010 + panel*1000000000 + players*100000000 + field_index*10000000 + seat*1000000 + game",
        "field_order": list(FIELDS),
        "opponent_fields": {
            "honest": "all baseline",
            "bluffing": "all bluff_heavy",
            "skeptical": "all challenge_heavy",
            "mixed": "opponents cycle baseline, bluff_heavy, challenge_heavy by game index; each player count uses n-1 opponents",
        },
        "game_max_turns": 1000,
        "win_denominator": "all scheduled games, including turn-limit draws",
        "checksums_sha256": checksums,
    }
    (output_dir / "study_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return summary, seats


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--games-per-seat", type=int, default=200)
    parser.add_argument("--players", type=int, nargs="+", default=[2, 3, 4, 5, 6])
    parser.add_argument("--fields", nargs="+", choices=FIELDS, default=list(FIELDS))
    parser.add_argument("--candidates", nargs="+", choices=CANDIDATES, default=list(CANDIDATES))
    parser.add_argument("--panel", type=int, default=0)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    summary_rows, seat_rows = run_study(args.output_dir, args.games_per_seat,
                                        args.players, args.fields, args.candidates, args.panel)
    print(f"Wrote {len(summary_rows)} matchup summaries and {len(seat_rows)} seat rows to {args.output_dir}")
