"""Supplemental heterogeneous-lineup benchmarks with explicit player identity."""
from coup_simulator import Game
from run_experiments import wilson


def table(players, policies, games=250, seed=20261101):
    if players != len(policies):
        raise ValueError("one policy per player is required")
    rows = []
    lineup = "/".join(policies)
    for rotation in range(players):
        rotated = policies[-rotation:] + policies[:-rotation] if rotation else list(policies)
        winner_counts = [0] * players
        draws = 0
        for game in range(games):
            winner = Game(players, seed + rotation * 100000 + game, rotated).run()
            if winner is None:
                draws += 1
            else:
                winner_counts[winner] += 1
        for original_index, focal in enumerate(policies):
            focal_seat = (original_index + rotation) % players
            assert rotated[focal_seat] == focal
            wins = winner_counts[focal_seat]
            lower, upper = wilson(wins, games)
            rows.append((
                players, lineup, original_index, focal_seat, focal, wins, games, draws,
                round(lower, 4), round(upper, 4),
            ))
    return rows


if __name__ == "__main__":
    print("players,lineup,player_id,seat,policy,wins,games,draws,lower95,upper95")
    for n in (2, 3, 4, 5, 6):
        for policies in (
            ["baseline"] * n,
            ["bluff_heavy"] * n,
            ["challenge_heavy"] * n,
            ["bluff_heavy", "challenge_heavy"] + ["baseline"] * (n - 2),
        ):
            for row in table(n, policies):
                print(",".join(map(str, row)))
