"""Complete-rotation inference for the separately frozen expansion study."""
from __future__ import annotations

from math import isfinite, log, sqrt
from statistics import NormalDist


class ExpansionDataError(ValueError):
    """Recorded outcomes do not match a complete, paired panel."""


def integer(value, name):
    if isinstance(value, bool):
        raise ExpansionDataError(f"{name} must be an integer")
    if isinstance(value, int):
        result = value
    elif isinstance(value, str) and value.isdecimal():
        result = int(value)
    else:
        raise ExpansionDataError(f"{name} must be an integer")
    if result < 0:
        raise ExpansionDataError(f"{name} must be nonnegative")
    return result


def panel(rows, players, candidates, blocks):
    """Require the exact roster, all rotations and identical candidate seeds."""
    if isinstance(players, bool) or not isinstance(players, int) or not 2 <= players <= 10:
        raise ExpansionDataError("players must be between two and ten")
    if isinstance(blocks, bool) or not isinstance(blocks, int) or blocks < 1:
        raise ExpansionDataError("blocks must be positive")
    names = tuple(candidates)
    if not names or len(set(names)) != len(names) or any(not isinstance(n, str) or not n for n in names):
        raise ExpansionDataError("distinct named candidates required")
    result = {name: {} for name in names}
    for row in rows:
        name = row.get("candidate")
        if name not in result:
            raise ExpansionDataError("unplanned candidate")
        block = integer(row.get("block"), "block")
        rotation = integer(row.get("rotation"), "rotation")
        seat = integer(row.get("focal_seat"), "focal_seat")
        seed = integer(row.get("seed"), "seed")
        won = integer(row.get("won"), "won")
        draw = integer(row.get("draw"), "draw")
        turns = integer(row.get("turns"), "turns")
        winner = None if row.get("winner") in (None, "") else integer(row["winner"], "winner")
        if (block >= blocks or rotation >= players or seat != rotation or
                (winner is not None and winner >= players) or turns < 1 or
                won != int(winner == seat) or draw != int(winner is None)):
            raise ExpansionDataError("invalid outcome, rotation or focal attribution")
        key = block, rotation
        if key in result[name]:
            raise ExpansionDataError("duplicate game")
        result[name][key] = (seed, won, draw, turns)
    expected = {(block, rotation) for block in range(blocks) for rotation in range(players)}
    for name, games in result.items():
        if games.keys() != expected:
            raise ExpansionDataError(f"incomplete panel for {name}")
        seeds = []
        for block in range(blocks):
            values = {games[block, rotation][0] for rotation in range(players)}
            if len(values) != 1:
                raise ExpansionDataError("rotation block has different seeds")
            seeds.append(values.pop())
        if len(set(seeds)) != blocks:
            raise ExpansionDataError("seed reused between independent blocks")
    first = result[names[0]]
    for games in result.values():
        if any(games[key][0] != first[key][0] for key in expected):
            raise ExpansionDataError("candidate panels use different seeds")
    return result


def paired_compare(rows, players, first, second, blocks, family_size,
                   alpha=0.05, practical_threshold=0.02):
    """Compare fixed candidates using independent complete rotation blocks.

    All sums involving outcomes use integers, avoiding platform-dependent float
    summation. The normal bound is approximate; the Hoeffding bound applies to
    the [-1, 1] paired block range, simultaneously within the declared family.
    """
    if first == second or blocks < 2:
        raise ExpansionDataError("two distinct candidates and at least two blocks required")
    if isinstance(family_size, bool) or not isinstance(family_size, int) or family_size < 1:
        raise ExpansionDataError("positive comparison family required")
    if not isfinite(alpha) or not 0 < alpha < 1 or not isfinite(practical_threshold) or not 0 <= practical_threshold < 1:
        raise ExpansionDataError("invalid inference settings")
    games = panel(rows, players, (first, second), blocks)
    numerators = [sum(games[first][block, r][1] - games[second][block, r][1]
                      for r in range(players)) for block in range(blocks)]
    total = sum(numerators)
    difference = total / (players * blocks)
    variance = (blocks * sum(n * n for n in numerators) - total * total) / (
        blocks * (blocks - 1) * players * players)
    normal_half = NormalDist().inv_cdf(1 - alpha / (2 * family_size)) * sqrt(variance / blocks)
    strict_half = sqrt(2 * log(2 * family_size / alpha) / blocks)
    normal_lower, normal_upper = max(-1., difference - normal_half), min(1., difference + normal_half)
    strict_lower, strict_upper = max(-1., difference - strict_half), min(1., difference + strict_half)
    first_wins = sum(v[1] for v in games[first].values())
    second_wins = sum(v[1] for v in games[second].values())
    return {
        "first": first, "second": second, "players": players, "blocks": blocks,
        "games_per_candidate": players * blocks,
        "first_wins": first_wins, "second_wins": second_wins,
        "first_draws": sum(v[2] for v in games[first].values()),
        "second_draws": sum(v[2] for v in games[second].values()),
        "first_rate": first_wins / (players * blocks),
        "second_rate": second_wins / (players * blocks), "difference": difference,
        "normal_family_lower": normal_lower, "normal_family_upper": normal_upper,
        "conservative_family_lower": strict_lower, "conservative_family_upper": strict_upper,
        "normal_supports_positive": normal_lower > 0,
        "normal_supports_practical": normal_lower > practical_threshold,
        "conservative_supports_positive": strict_lower > 0,
        "conservative_supports_practical": strict_lower > practical_threshold,
        "family_size": family_size, "alpha": alpha, "practical_threshold": practical_threshold,
    }
