"""Validation and paired, complete-rotation-block comparisons for Coup studies.

This module reads raw game rows. It does not import the game engine or change
the frozen 2026-10-10 study. A block uses one seed and contains each focal seat
exactly once. Candidate panels are paired only when blocks, seeds, rotations,
and focal seats match exactly.
"""
from __future__ import annotations

from collections import defaultdict
from math import isfinite, log, sqrt
from statistics import NormalDist
from typing import Iterable, Mapping


class StudyDataError(ValueError):
    """Raw outcomes do not satisfy the declared experiment design."""


def _integer(value: object, name: str) -> int:
    if isinstance(value, bool):
        raise StudyDataError(f"{name} must be an integer")
    if isinstance(value, int):
        result = value
    elif isinstance(value, str) and value.isdecimal():
        result = int(value)
    else:
        raise StudyDataError(f"{name} must be an integer")
    if result < 0:
        raise StudyDataError(f"{name} must be nonnegative")
    return result


def _bit(value: object, name: str) -> int:
    result = _integer(value, name)
    if result not in (0, 1):
        raise StudyDataError(f"{name} must be zero or one")
    return result


def _value(row: Mapping[str, object], name: str) -> object:
    try:
        return row[name]
    except KeyError as exc:
        raise StudyDataError(f"missing raw-game column: {name}") from exc


def _panel(rows: Iterable[Mapping[str, object]], *, stage: str, players: int,
           field: str, candidates: tuple[str, ...], expected_blocks: int | None = None) -> dict:
    panel = {name: defaultdict(dict) for name in candidates}
    for row in rows:
        if row.get("stage") != stage or row.get("field") != field:
            continue
        if _integer(_value(row, "players"), "players") != players:
            continue
        candidate = _value(row, "candidate")
        if candidate not in candidates:
            continue
        block = _integer(_value(row, "block"), "block")
        rotation = _integer(_value(row, "rotation"), "rotation")
        focal_seat = _integer(_value(row, "focal_seat"), "focal_seat")
        seed = _integer(_value(row, "seed"), "seed")
        turns = _integer(_value(row, "turns"), "turns")
        won = _bit(_value(row, "won"), "won")
        draw = _bit(_value(row, "draw"), "draw")
        raw_winner = _value(row, "winner")
        winner = None if raw_winner is None or raw_winner == "" else _integer(raw_winner, "winner")
        if rotation >= players or focal_seat >= players or (winner is not None and winner >= players):
            raise StudyDataError("rotation, focal seat, or winner is outside the player count")
        if draw != int(winner is None) or won != int(winner == focal_seat):
            raise StudyDataError("won/draw does not match the winner and distinct focal seat")
        if turns == 0:
            raise StudyDataError("a scheduled game must execute at least one turn")
        if rotation in panel[candidate][block]:
            raise StudyDataError(f"duplicate game for {candidate}, block {block}, rotation {rotation}")
        panel[candidate][block][rotation] = (seed, focal_seat, won, draw)

    expected_rotations = set(range(players))
    for candidate in candidates:
        if not panel[candidate]:
            raise StudyDataError(f"no rows for candidate {candidate}")
        seeds_by_block = {}
        for block, rotations in panel[candidate].items():
            if set(rotations) != expected_rotations:
                raise StudyDataError(f"incomplete rotation block for {candidate}, block {block}")
            seats = [values[1] for values in rotations.values()]
            if set(seats) != expected_rotations:
                raise StudyDataError(f"focal seats are not balanced for {candidate}, block {block}")
            seeds = {values[0] for values in rotations.values()}
            if len(seeds) != 1:
                raise StudyDataError(f"multiple initial seeds in {candidate}, block {block}")
            seeds_by_block[block] = seeds.pop()
        if len(set(seeds_by_block.values())) != len(seeds_by_block):
            raise StudyDataError(f"seed reused across blocks for {candidate}")
    reference = candidates[0]
    if expected_blocks is not None and set(panel[reference]) != set(range(expected_blocks)):
        raise StudyDataError("panel does not contain the exact planned block IDs")
    for candidate in candidates[1:]:
        if set(panel[reference]) != set(panel[candidate]):
            raise StudyDataError("candidate panels have different block identities")
        for block in panel[reference]:
            for rotation in range(players):
                if panel[reference][block][rotation][:2] != panel[candidate][block][rotation][:2]:
                    raise StudyDataError("paired games differ in seed or focal seat")
    return panel


def audit_panel(rows: Iterable[Mapping[str, object]], players: int, field: str,
                candidates: Iterable[str], expected_blocks: int, *,
                stage: str = "confirmation") -> dict:
    """Check exact candidate and block coverage before a panel is interpreted."""
    names = tuple(candidates)
    if not isinstance(players, int) or isinstance(players, bool) or not 2 <= players <= 6:
        raise ValueError("players must be between two and six")
    if not isinstance(field, str) or not field or not isinstance(stage, str) or not stage:
        raise ValueError("field and stage must be nonempty strings")
    if not names or len(set(names)) != len(names) or any(not isinstance(name, str) or not name for name in names):
        raise ValueError("provide distinct, nonempty candidate IDs")
    if not isinstance(expected_blocks, int) or isinstance(expected_blocks, bool) or expected_blocks < 1:
        raise ValueError("expected_blocks must be a positive integer")
    saved = list(rows)
    observed = {
        _value(row, "candidate") for row in saved
        if row.get("stage") == stage and row.get("field") == field and
        _integer(_value(row, "players"), "players") == players
    }
    if observed != set(names):
        raise StudyDataError("panel candidate roster differs from the frozen plan")
    panel = _panel(saved, stage=stage, players=players, field=field,
                   candidates=names, expected_blocks=expected_blocks)
    return {
        "stage": stage, "players": players, "field": field,
        "candidates": list(names), "blocks": expected_blocks,
        "games_per_candidate": players * expected_blocks,
        "wins": {name: sum(values[2] for rotations in panel[name].values()
                           for values in rotations.values()) for name in names},
        "draws": {name: sum(values[3] for rotations in panel[name].values()
                            for values in rotations.values()) for name in names},
    }


def paired_compare(rows: Iterable[Mapping[str, object]], players: int, field: str,
                   first: str, second: str, alpha: float = 0.05,
                   family_size: int = 35, *, stage: str = "confirmation",
                   practical_threshold: float = 0.02,
                   min_blocks: int = 30,
                   expected_blocks: int | None = None) -> dict:
    """Compare two frozen candidates using complete, shared rotation blocks.

    The normal interval uses a Bonferroni z value and sample variation of the
    paired block differences. It is approximate. The Hoeffding interval uses
    the [-1, 1] range of a paired block difference and a union bound, giving
    a conservative finite-sample family bound when blocks are independent.
    Selection on these same rows invalidates confirmation interpretation.
    """
    if not isinstance(players, int) or isinstance(players, bool) or not 2 <= players <= 6:
        raise ValueError("players must be between two and six")
    if not isinstance(field, str) or not field or not isinstance(stage, str) or not stage:
        raise ValueError("field and stage must be nonempty strings")
    if not isinstance(first, str) or not isinstance(second, str) or not first or not second or first == second:
        raise ValueError("two distinct candidate IDs are required")
    if not isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must be between zero and one")
    if not isinstance(family_size, int) or isinstance(family_size, bool) or family_size < 1:
        raise ValueError("family_size must be a positive integer")
    if not isfinite(practical_threshold) or not 0 <= practical_threshold < 1:
        raise ValueError("practical_threshold must be in [0, 1)")
    if not isinstance(min_blocks, int) or isinstance(min_blocks, bool) or min_blocks < 2:
        raise ValueError("min_blocks must be at least two")
    if expected_blocks is not None and (not isinstance(expected_blocks, int) or
                                        isinstance(expected_blocks, bool) or expected_blocks < 1):
        raise ValueError("expected_blocks must be a positive integer")

    panel = _panel(rows, stage=stage, players=players, field=field,
                   candidates=(first, second), expected_blocks=expected_blocks)
    blocks = sorted(panel[first])
    count = len(blocks)
    if count < min_blocks:
        raise StudyDataError(f"{count} independent blocks; need at least {min_blocks}")
    first_wins = second_wins = first_draws = second_draws = 0
    differences = []
    for block in blocks:
        first_games = panel[first][block]
        second_games = panel[second][block]
        wins_a = sum(first_games[rotation][2] for rotation in range(players))
        wins_b = sum(second_games[rotation][2] for rotation in range(players))
        first_wins += wins_a
        second_wins += wins_b
        first_draws += sum(first_games[rotation][3] for rotation in range(players))
        second_draws += sum(second_games[rotation][3] for rotation in range(players))
        differences.append((wins_a - wins_b) / players)
    difference = sum(differences) / count
    sample_variance = sum((value - difference) ** 2 for value in differences) / (count - 1)
    z = NormalDist().inv_cdf(1 - alpha / (2 * family_size))
    normal_half_width = z * sqrt(sample_variance / count)
    conservative_half_width = sqrt(2 * log(2 * family_size / alpha) / count)
    normal_lower = max(-1.0, difference - normal_half_width)
    normal_upper = min(1.0, difference + normal_half_width)
    conservative_lower = max(-1.0, difference - conservative_half_width)
    conservative_upper = min(1.0, difference + conservative_half_width)
    games = count * players
    return {
        "stage": stage, "players": players, "field": field,
        "first": first, "second": second,
        "blocks": count, "games_per_candidate": games,
        "first_wins": first_wins, "second_wins": second_wins,
        "first_draws": first_draws, "second_draws": second_draws,
        "first_rate": first_wins / games, "second_rate": second_wins / games,
        "difference": difference,
        "normal_family_lower": normal_lower, "normal_family_upper": normal_upper,
        "conservative_family_lower": conservative_lower,
        "conservative_family_upper": conservative_upper,
        "normal_supports_positive": normal_lower > 0,
        "normal_supports_practical": normal_lower > practical_threshold,
        "conservative_supports_positive": conservative_lower > 0,
        "alpha": alpha, "family_size": family_size,
        "practical_threshold": practical_threshold,
    }
