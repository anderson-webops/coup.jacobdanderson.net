"""Seeded simulator for the standard Coup court deck and turn rules.

Policies receive only their own cards and public information. They are small,
named heuristics, not claims of optimal play.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from random import Random

ROLES = ("duke", "assassin", "captain", "ambassador", "contessa")
CLAIMS = {"tax": "duke", "assassinate": "assassin", "steal": "captain", "exchange": "ambassador"}
BLOCKS = {"foreign_aid": ("duke",), "assassinate": ("contessa",), "steal": ("captain", "ambassador")}
POLICIES = (
    "baseline", "income", "foreign_aid", "taxer", "captain", "assassin",
    "exchange", "bluff_heavy", "challenge_low", "challenge_heavy",
    "block_aggressive", "challenge_aggressive",
)


@dataclass
class Player:
    policy: str
    coins: int = 2
    cards: list[str] = field(default_factory=list)
    revealed: list[str] = field(default_factory=list)
    alive: bool = True

    def influence(self) -> int:
        return len(self.cards)


class Game:
    def __init__(self, n=4, seed=1, policies=None, max_turns=1000):
        if n < 2 or n > 6:
            raise ValueError("standard Coup supports 2-6 players")
        if max_turns < 1:
            raise ValueError("max_turns must be positive")
        policy_names = list(policies) if policies is not None else ["baseline"] * n
        if len(policy_names) != n or any(name not in POLICIES for name in policy_names):
            raise ValueError("provide one known policy per player")
        self.rng = Random(seed)
        self.max_turns = max_turns
        self.turn = 0
        self.events: list[tuple] = []
        self.failed_streak = [0] * n
        self.deck = [role for role in ROLES for _ in range(3)]
        self.rng.shuffle(self.deck)
        self.players = [Player(name) for name in policy_names]
        if n == 2:
            self.players[0].coins = 1  # base-game two-player rule
        for player in self.players:
            player.cards = [self.deck.pop(), self.deck.pop()]

    def alive(self) -> list[int]:
        return [i for i, player in enumerate(self.players) if player.alive]

    def observation(self, i: int) -> dict:
        """A policy view: private own cards and only public opponent state."""
        return {
            "self_cards": tuple(self.players[i].cards),
            "self_coins": self.players[i].coins,
            "public": tuple(
                (p.coins, p.influence(), tuple(p.revealed)) for p in self.players
            ),
        }

    def assert_valid_state(self) -> None:
        cards = list(self.deck)
        for player in self.players:
            cards.extend(player.cards)
            cards.extend(player.revealed)
            assert player.alive == (len(player.cards) > 0)
            assert player.coins >= 0
            assert player.alive or player.coins == 0
        assert Counter(cards) == Counter({role: 3 for role in ROLES})

    def _eligible_target(self, actor: int) -> list[int]:
        return [j for j in self.alive() if j != actor]

    def _target(self, actor: int, action: str) -> int:
        candidates = self._eligible_target(actor)
        if action == "steal":
            score = lambda j: self.players[j].coins
        else:
            score = lambda j: (
                self.players[j].influence() == 1,
                self.players[j].coins >= 7,
                self.players[j].coins,
            )
        best = max(score(j) for j in candidates)
        return self.rng.choice([j for j in candidates if score(j) == best])

    def _lose(self, player_index: int, forced: str | None = None) -> None:
        player = self.players[player_index]
        if not player.cards:
            return
        # Every policy uses the same simple, legal influence-choice heuristic.
        rank = {"contessa": 0, "ambassador": 1, "assassin": 2, "captain": 3, "duke": 4}
        card = forced if forced in player.cards else min(player.cards, key=rank.get)
        player.cards.remove(card)
        player.revealed.append(card)
        self.events.append(("lose", player_index, card))
        if not player.cards:
            player.alive = False
            player.coins = 0
            self.events.append(("eliminate", player_index))

    def _replace_proved_card(self, player_index: int, role: str) -> None:
        player = self.players[player_index]
        player.cards.remove(role)
        self.deck.append(role)
        self.rng.shuffle(self.deck)
        player.cards.append(self.deck.pop())

    def _wants_challenge(self, challenger: int, role: str) -> bool:
        player = self.players[challenger]
        view = self.observation(challenger)
        publicly_accounted = view["self_cards"].count(role) + sum(
            exposed.count(role) for _, _, exposed in view["public"]
        )
        if publicly_accounted == 3:
            return True
        if player.policy in ("challenge_heavy", "challenge_aggressive"):
            return True
        if player.policy == "challenge_low" and role in ("assassin", "captain", "contessa"):
            return self.rng.random() < 0.15
        return False

    def _challenger(self, claimant: int, role: str) -> int | None:
        # Clockwise priority is a reproducible convention where the rulebook
        # leaves simultaneous responses to the table.
        n = len(self.players)
        for offset in range(1, n):
            j = (claimant + offset) % n
            if self.players[j].alive and self._wants_challenge(j, role):
                return j
        return None

    def _claim_stands(self, claimant: int, role: str) -> bool:
        challenger = self._challenger(claimant, role)
        if challenger is None:
            return True
        self.events.append(("challenge", challenger, claimant, role))
        if role in self.players[claimant].cards:
            self._lose(challenger)
            self._replace_proved_card(claimant, role)
            self.events.append(("proved", claimant, role))
            return True
        self._lose(claimant)
        self.events.append(("disproved", claimant, role))
        return False

    def _block(self, actor: int, action: str, target: int | None = None) -> tuple[int, str] | None:
        if action not in BLOCKS:
            return None
        n = len(self.players)
        for offset in range(1, n):
            j = (actor + offset) % n
            if not self.players[j].alive or (target is not None and j != target):
                continue
            held = self.observation(j)["self_cards"]
            valid = next((role for role in BLOCKS[action] if role in held), None)
            if valid is not None:
                return j, valid
            if self.players[j].policy in ("block_aggressive", "bluff_heavy"):
                return j, BLOCKS[action][0]
        return None

    def _choose_action(self, i: int) -> str:
        player = self.players[i]
        cards = self.observation(i)["self_cards"]
        targets = self._eligible_target(i)
        if player.coins >= 7:
            return "coup"
        if self.failed_streak[i] >= 2:
            return "income"
        policy = player.policy
        if policy == "income":
            return "income"
        if policy == "foreign_aid":
            return "foreign_aid"
        if policy in ("taxer", "bluff_heavy"):
            return "tax"
        if policy == "captain":
            return "steal" if any(self.players[j].coins for j in targets) else "foreign_aid"
        if policy == "assassin":
            return "assassinate" if player.coins >= 3 else "foreign_aid"
        if policy == "exchange" and "ambassador" in cards and "duke" not in cards:
            return "exchange" if self.rng.random() < 0.45 else "foreign_aid"
        # The baseline and response-focused policies make only truthful claims.
        if "duke" in cards:
            return "tax"
        if "captain" in cards and any(self.players[j].coins for j in targets):
            return "steal"
        if "assassin" in cards and player.coins >= 3 and any(
            self.players[j].influence() == 1 for j in targets
        ):
            return "assassinate"
        if "ambassador" in cards and player.coins < 4 and self.rng.random() < 0.2:
            return "exchange"
        return "foreign_aid"

    def _exchange(self, i: int) -> None:
        player = self.players[i]
        keep_count = len(player.cards)
        drawn = [self.deck.pop(), self.deck.pop()]
        pool = player.cards + drawn
        rank = {"duke": 5, "captain": 4, "assassin": 3, "contessa": 2, "ambassador": 1}
        selected_indices = sorted(range(len(pool)), key=lambda k: (-rank[pool[k]], k))[:keep_count]
        selected = set(selected_indices)
        player.cards = [card for k, card in enumerate(pool) if k in selected]
        self.deck.extend(card for k, card in enumerate(pool) if k not in selected)
        self.rng.shuffle(self.deck)
        self.events.append(("exchange", i))

    def step(self, i: int) -> None:
        player = self.players[i]
        if not player.alive:
            return
        action = self._choose_action(i)
        target = self._target(i, action) if action in ("coup", "assassinate", "steal") else None
        self.events.append(("action", i, action, target))
        if action == "income":
            player.coins += 1
            self.failed_streak[i] = 0
            return
        if action == "coup":
            player.coins -= 7
            self._lose(target)
            self.failed_streak[i] = 0
            return
        if action == "assassinate":
            player.coins -= 3
        claim = CLAIMS.get(action)
        if claim is not None and not self._claim_stands(i, claim):
            if action == "assassinate" and player.alive:
                player.coins += 3  # successful action challenge refunds the fee
            self.failed_streak[i] += 1
            return
        block = self._block(i, action, target)
        if block is not None:
            blocker, role = block
            self.events.append(("block", blocker, role, action))
            if self._claim_stands(blocker, role):
                self.failed_streak[i] += 1
                return  # a successful block keeps an assassination fee spent
        if action == "foreign_aid":
            player.coins += 2
        elif action == "tax":
            player.coins += 3
        elif action == "assassinate":
            self._lose(target)
        elif action == "steal":
            amount = min(2, self.players[target].coins)
            self.players[target].coins -= amount
            player.coins += amount
        elif action == "exchange":
            self._exchange(i)
        self.failed_streak[i] = 0

    def run(self) -> int | None:
        i = 0
        while len(self.alive()) > 1 and self.turn < self.max_turns:
            if self.players[i].alive:
                self.step(i)
                self.turn += 1
            i = (i + 1) % len(self.players)
        return self.alive()[0] if len(self.alive()) == 1 else None


def experiment(games=10000, players=4, seed=20261010, policies=None):
    names = list(policies) if policies is not None else ["baseline"] * players
    wins = Counter()
    completed = 0
    for game_index in range(games):
        winner = Game(players, seed + game_index, names).run()
        if winner is not None:
            wins[winner] += 1
            completed += 1
    return {seat: wins[seat] / games for seat in range(players)}, completed / games


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--players", type=int, default=4)
    parser.add_argument("-g", "--games", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20261010)
    args = parser.parse_args()
    print(experiment(args.games, args.players, args.seed))
