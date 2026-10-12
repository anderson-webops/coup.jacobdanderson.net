"""Public-information strategy search layered on the frozen Coup rules engine.

This module adds policy choices, not new game rules. Card availability is an
exact uniform-card prior; claim likelihoods and state values are heuristics.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import asdict, dataclass, replace
from math import comb
from random import Random

from coup_simulator import BLOCKS, CLAIMS, POLICIES, ROLES, Game


@dataclass(frozen=True)
class Config:
    name: str
    bluff: float = 0.15
    block_bluff: float = 0.1
    assumed_bluff: float = 0.25
    challenge_scale: float = 1.0
    coup_at: int = 7
    attack: float = 1.0
    exchange: float = 0.15
    defense: float = 1.0
    history: bool = False
    card_aware: bool = True
    target: str = 'threat'
    random_actions: bool = False


def availability(view, claimant, role):
    """P(role in h cards) under uniform unknown-card allocation, without claims."""
    known = view['self_cards'].count(role) + sum(p[2].count(role) for p in view['public'])
    copies = 3 - known
    unknown = 15 - len(view['self_cards']) - sum(len(p[2]) for p in view['public'])
    hand = view['public'][claimant][1]
    if copies <= 0 or hand <= 0:
        return 0.0
    if unknown < hand or copies > unknown:
        raise ValueError('Inconsistent public card observation')
    return 1.0 - (comb(unknown - copies, hand) if unknown - copies >= hand else 0) / comb(unknown, hand)


def no_opponent_role_probability(view, role):
    """Uniform-card prior that all remaining copies are in the deck."""
    known = view['self_cards'].count(role) + sum(p[2].count(role) for p in view['public'])
    copies = 3 - known
    unknown = 15 - len(view['self_cards']) - sum(len(p[2]) for p in view['public'])
    opponent_cards = sum(p[1] for j, p in enumerate(view['public']) if j != view['seat'])
    deck_cards = unknown - opponent_cards
    if not 0 <= copies <= unknown or not 0 <= deck_cards <= unknown:
        raise ValueError('Inconsistent public card observation')
    return (comb(deck_cards, copies) / comb(unknown, copies)) if copies <= deck_cards else 0.0


def claim_probability(view, claimant, role, config):
    prior = availability(view, claimant, role) if config.card_aware else 0.4
    if prior == 0:
        return 0.0
    likelihood = config.assumed_bluff
    if config.history:
        # Beta-smoothed public proof record approximates a claimant's reliability.
        # Proven cards are replaced: this is behavioral evidence, not ownership.
        proved = sum(e[0] == 'proved' and e[1] == claimant for e in view['history'])
        false = sum(e[0] == 'disproved' and e[1] == claimant for e in view['history'])
        likelihood = (likelihood * 4 + false) / (4 + proved + false)
    return prior / (prior + (1 - prior) * likelihood)


def challenge(view, claimant, role, config):
    if config.card_aware and availability(view, claimant, role) == 0:
        return True
    probability = claim_probability(view, claimant, role, config)
    own = view['seat']
    event = view['history'][-1] if view['history'] else None
    alive = sum(p[1] > 0 for p in view['public'])
    gain = 1 / max(1, alive - 1)  # multiplayer benefit is shared
    loss = 1.0 if len(view['self_cards']) > 1 else 2.0
    if event and event[0] == 'action' and event[3] == own:
        if event[2] == 'assassinate':
            if 'contessa' in view['self_cards']:
                # A truthful block is still available after passing the challenge.
                loss += 1.0
            else:
                gain += 2.0 if len(view['self_cards']) == 1 else 1.0
                # A truthful Assassin may eliminate a two-card challenger.
                if len(view['self_cards']) > 1:
                    loss += 1.5
                # A one-card target can instead try a desperate Contessa block;
                # passing is therefore not certain elimination.
        elif event[2] == 'steal':
            gain += min(2, view['self_coins']) * 0.25
    if event and event[0] == 'block':
        # If our action is blocked, a false block challenge can recover its value.
        action = next((e for e in reversed(view['history'][:-1]) if e[0] == 'action'), None)
        if action and action[1] == own:
            gain += {'foreign_aid': 0.5, 'steal': 0.5, 'assassinate': config.attack}.get(action[2], 0)
    return (1 - probability) * gain * config.challenge_scale > probability * loss


def card_value(role, view, config):
    others = [p for i, p in enumerate(view['public']) if i != view['seat'] and p[1] > 0]
    if role == 'duke':
        return 4.5 if view['self_coins'] < 7 else 3.5
    if role == 'captain':
        return 2.5 + min(1.5, sum(p[0] for p in others) / max(1, len(others)) / 3)
    if role == 'assassin':
        return 1.8 + config.attack * (0.9 if view['self_coins'] >= 3 else 0.2)
    if role == 'contessa':
        return 1.2 + config.defense * (1.0 + sum(p[0] >= 3 for p in others) / max(1, len(others)))
    return 1.5 + (0.5 if 'duke' not in view['self_cards'] else 0)


def target_candidates(view, action, config):
    targets = [j for j, p in enumerate(view['public']) if j != view['seat'] and p[1] > 0]
    if not targets:
        raise ValueError('Targeted action requires a live opponent')
    if config.target == 'random':
        return targets
    def score(j):
        coins, influence, _ = view['public'][j]
        if action == 'steal':
            return min(2, coins) - 0.8 * (availability(view, j, 'captain') + availability(view, j, 'ambassador'))
        if config.target == 'richest':
            return coins
        return 2.5 * (influence == 1) + coins / 7 - (availability(view, j, 'contessa') if action == 'assassinate' else 0)
    best = max(score(j) for j in targets)
    return [j for j in targets if score(j) == best]


def pick_target(view, action, config, rng):
    return rng.choice(target_candidates(view, action, config))


def decision_seed(game_seed, seat):
    """Keep each seat's choices in a reproducible, domain-separated stream."""
    data = f'coup-research-decisions-v1:{game_seed}:{seat}'.encode('ascii')
    return int.from_bytes(hashlib.sha256(data).digest(), 'big')


def choose_action(view, config, rng):
    coins = view['self_coins']
    cards = view['self_cards']
    if coins >= 10:
        return 'coup'
    if config.random_actions:
        legal = ['income', 'foreign_aid', 'tax', 'steal', 'exchange']
        if coins >= 3: legal.append('assassinate')
        if coins >= 7: legal.append('coup')
        return rng.choice(legal)
    if coins >= config.coup_at:
        return 'coup'
    if view['failed_streak'] >= 2:
        return 'income'
    # Estimated public challenge pressure controls whether to risk a false claim.
    claims = sum(e[0] == 'block' or (e[0] == 'action' and e[2] in CLAIMS) for e in view['history'])
    challenges = sum(e[0] == 'challenge' for e in view['history'])
    pressure = min(1, (challenges + 2) / (claims + 8)) if config.history else 0.2
    risk_bluff = rng.random() < config.bluff * (1 - pressure if config.history else 1)
    options = [('income', 1.0)]
    options.append(('foreign_aid', 2 * no_opponent_role_probability(view, 'duke')))
    if 'duke' in cards:
        options.append(('tax', 3.0))
    elif risk_bluff:
        options.append(('tax', 3 * (1 - pressure) - 2 * pressure))
    if 'captain' in cards or risk_bluff:
        possible = target_candidates(view, 'steal', config)
        value = sum(
            min(2, view['public'][target][0]) *
            (1 - min(1, availability(view, target, 'captain') + availability(view, target, 'ambassador')))
            for target in possible
        ) / len(possible)
        options.append(('steal', value - (0 if 'captain' in cards else 2 * pressure)))
    if coins >= 3 and ('assassin' in cards or risk_bluff):
        possible = target_candidates(view, 'assassinate', config)
        value = sum(
            (3.5 if view['public'][target][1] == 1 else 1.8) *
            (1 - availability(view, target, 'contessa'))
            for target in possible
        ) / len(possible)
        options.append(('assassinate', config.attack * value - 0.7 - (0 if 'assassin' in cards else 2 * pressure)))
    if 'ambassador' in cards and 'duke' not in cards and rng.random() < config.exchange:
        options.append(('exchange', 2.2))
    best = max(value for _, value in options)
    return rng.choice([action for action, value in options if value == best])


PRESETS = {
    'card_cautious': Config('card_cautious', bluff=0, block_bluff=0, assumed_bluff=0.08, challenge_scale=0.6),
    'card_balanced': Config('card_balanced'),
    'card_bold': Config('card_bold', bluff=0.7, block_bluff=0.35, assumed_bluff=0.45, challenge_scale=1.8),
    'public_learning': Config('public_learning', history=True, bluff=0.4, block_bluff=0.2),
    'eliminator': Config('eliminator', attack=1.8, assumed_bluff=0.3, challenge_scale=1.2),
    'defensive': Config('defensive', defense=2.0, attack=0.6, bluff=0.05, block_bluff=0),
    'exchange_builder': Config('exchange_builder', exchange=0.7, attack=0.8),
    'public_random': Config('public_random', random_actions=True, bluff=0.5, block_bluff=0.15),
}
# Deterministic finite candidate grid, specified before any new outcome is read.
for index in range(24):
    PRESETS[f'search_{index:02d}'] = Config(
        f'search_{index:02d}', bluff=(0.0, 0.2, 0.6)[index % 3],
        block_bluff=(0.0, 0.15, 0.45)[(index // 3) % 3],
        assumed_bluff=(0.1, 0.35)[(index // 9) % 2],
        challenge_scale=(0.7, 1.5)[index % 2], coup_at=(7, 9)[(index // 2) % 2],
        attack=(0.8, 1.5)[(index // 4) % 2], exchange=(0.1, 0.55)[(index // 6) % 2],
        defense=(0.8, 1.5)[(index // 5) % 2], history=bool((index // 3) % 2),
        target=('threat', 'richest')[(index // 7) % 2],
    )
PRESETS.update({
    'ablate_no_claim_cards': replace(PRESETS['public_learning'], name='ablate_no_claim_cards', card_aware=False),
    'ablate_no_history': replace(PRESETS['public_learning'], name='ablate_no_history', history=False),
    'ablate_random_target': replace(PRESETS['public_learning'], name='ablate_random_target', target='random'),
    'ablate_fixed_retention': replace(PRESETS['public_learning'], name='ablate_fixed_retention'),
})


class ResearchGame(Game):
    def __init__(self, n=4, seed=1, policies=None, max_turns=1000, strict=False):
        names = list(policies) if policies is not None else ['card_balanced'] * n
        if len(names) != n or any(p not in POLICIES and p not in PRESETS for p in names):
            raise ValueError('One known research strategy per player required')
        super().__init__(n, seed, [p if p in POLICIES else 'baseline' for p in names], max_turns)
        self.names = names
        self.decision_rng = [Random(decision_seed(seed, i)) for i in range(n)]
        self.strict = strict
        self.action_counts = Counter()

    def view(self, i):
        result = self.observation(i)
        result.update(seat=i, history=tuple(self.events), failed_streak=self.failed_streak[i])
        return result

    def _legacy_decision(self, i, method, *args):
        environment = self.rng
        self.rng = self.decision_rng[i]
        try:
            return method(*args)
        finally:
            self.rng = environment

    def _choose_action(self, i):
        if self.players[i].coins >= 10:
            action = 'coup'
        elif self.names[i] in PRESETS:
            action = choose_action(self.view(i), PRESETS[self.names[i]], self.decision_rng[i])
        else:
            action = self._legacy_decision(i, super()._choose_action, i)
        coins = self.players[i].coins
        if action not in ('income', 'foreign_aid', 'tax', 'steal', 'assassinate', 'exchange', 'coup'):
            raise ValueError('Unknown action')
        if (action == 'coup' and coins < 7) or (action == 'assassinate' and coins < 3):
            raise ValueError('Unaffordable action')
        self.action_counts[action] += 1
        return action

    def _target(self, i, action):
        if self.names[i] in PRESETS:
            return pick_target(self.view(i), action, PRESETS[self.names[i]], self.decision_rng[i])
        return self._legacy_decision(i, super()._target, i, action)

    def _challenger(self, claimant, role):
        for offset in range(1, len(self.players)):
            j = (claimant + offset) % len(self.players)
            if not self.players[j].alive:
                continue
            if self.names[j] in PRESETS:
                wants = challenge(self.view(j), claimant, role, PRESETS[self.names[j]])
            else:
                wants = self._legacy_decision(j, super()._wants_challenge, j, role)
            if wants:
                return j
        return None

    def _block(self, actor, action, target=None):
        if action not in BLOCKS:
            return None
        for off in range(1, len(self.players)):
            j = (actor + off) % len(self.players)
            if not self.players[j].alive or (target is not None and j != target):
                continue
            held = self.players[j].cards
            role = next((r for r in BLOCKS[action] if r in held), None)
            if role:
                return j, role
            if self.names[j] in PRESETS:
                cfg = PRESETS[self.names[j]]
                # A last-influence assassination victim has no survival cost to bluff a block.
                desperate = action == 'assassinate' and len(held) == 1
                if desperate or self.decision_rng[j].random() < cfg.block_bluff:
                    return j, BLOCKS[action][0]
            elif self.players[j].policy in ('block_aggressive', 'bluff_heavy'):
                return j, BLOCKS[action][0]
        return None

    def _lose(self, i, forced=None):
        if self.names[i] in PRESETS and self.players[i].cards and forced is None and self.names[i] != 'ablate_fixed_retention':
            cfg = PRESETS[self.names[i]]
            forced = min(self.players[i].cards, key=lambda role: card_value(role, self.view(i), cfg))
        return super()._lose(i, forced)

    def _exchange(self, i):
        if self.names[i] not in PRESETS or self.names[i] == 'ablate_fixed_retention':
            return super()._exchange(i)
        p = self.players[i]
        count = len(p.cards)
        pool = p.cards + [self.deck.pop(), self.deck.pop()]
        cfg, view = PRESETS[self.names[i]], self.view(i)
        selected = set(sorted(range(len(pool)), key=lambda k: (-card_value(pool[k], view, cfg), k))[:count])
        p.cards = [card for k, card in enumerate(pool) if k in selected]
        self.deck.extend(card for k, card in enumerate(pool) if k not in selected)
        self.rng.shuffle(self.deck)
        self.events.append(('exchange', i))

    def validate(self):
        cards = list(self.deck)
        for p in self.players:
            cards += p.cards + p.revealed
            if p.alive != bool(p.cards) or not 0 <= len(p.cards) <= 2 or p.coins < 0 or (not p.alive and p.coins != 0):
                raise ValueError('Invalid influence/coin state')
        if Counter(cards) != Counter({r: 3 for r in ROLES}):
            raise ValueError('Card conservation failed')

    def step(self, i):
        super().step(i)
        if self.strict:
            self.validate()


def configurations():
    return {name: asdict(config) for name, config in sorted(PRESETS.items())}
