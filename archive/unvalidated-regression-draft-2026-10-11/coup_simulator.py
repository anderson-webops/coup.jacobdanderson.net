"""Reproducible standard Coup simulator with legal-information policies."""
from __future__ import annotations
from dataclasses import dataclass, field
from random import Random
from collections import Counter
from typing import Optional

ROLES = ("duke", "assassin", "captain", "ambassador", "contessa")
CLAIMS = {"tax":"duke", "assassinate":"assassin", "steal":"captain", "exchange":"ambassador"}
BLOCKS = {"foreign_aid": ("duke",), "assassinate": ("contessa",), "steal": ("captain", "ambassador")}

@dataclass
class Player:
    policy: str
    coins: int = 2
    cards: list[str] = field(default_factory=list)
    alive: bool = True

    def influence(self): return len(self.cards)

class Game:
    def __init__(self, n=4, seed=1, policies=None, max_turns=1000):
        if n < 2 or n > 6: raise ValueError("standard Coup supports 2-6 players; use 3-6 for base setup")
        self.rng=Random(seed); self.max_turns=max_turns; self.turn=0; self.events=[]
        self.deck=[r for r in ROLES for _ in range(3)]; self.rng.shuffle(self.deck)
        ps=policies or ["baseline"]*n
        self.players=[Player(ps[i%len(ps)]) for i in range(n)]
        if n==2: self.players[0].coins=1
        for p in self.players: p.cards=[self.deck.pop(),self.deck.pop()]

    def alive(self): return [i for i,p in enumerate(self.players) if p.alive]
    def observation(self, i):
        """Legal information for player i; never includes opponent cards/deck order."""
        return {"self_cards":tuple(self.players[i].cards), "self_coins":self.players[i].coins,
                "public":tuple((p.coins,p.influence(),p.alive) for p in self.players)}
    def _eligible_target(self, i): return [j for j in self.alive() if j!=i and self.players[j].influence()]
    def _choose_action(self, i, obs):
        p=self.players[i]
        if p.coins>=10: return "coup"
        if p.policy in ("taxer","bluff_heavy"): return "tax"
        if p.policy in ("assassin",) and obs["self_coins"]>=3 and self._eligible_target(i): return "assassinate"
        if p.policy=="captain" and self._eligible_target(i): return "steal"
        if p.policy=="foreign_aid": return "foreign_aid"
        if p.policy=="exchange": return "exchange"
        return self.rng.choice(["income","foreign_aid","tax","steal"])
    def _policy_challenge(self, j, claim, obs):
        if self.players[j].policy in ("challenge_aggressive","challenge_heavy"): return True
        counts={r:0 for r in ROLES}
        for e in self.events:
            if e[0]=="lose": counts[e[2]]+=1
        return claim is not None and counts.get(claim,0)>=3
    def _policy_block(self, j, action, obs):
        allowed=BLOCKS[action]
        for role in allowed:
            if role in obs["self_cards"]: return role
        if self.players[j].policy in ("block_aggressive","bluff_heavy"): return allowed[0]
        return None
    def _policy_loss(self, j, obs): return obs["self_cards"][0]
    def _lose(self, j, forced=None):
        p=self.players[j]
        if not p.cards: return
        card=forced if forced in p.cards else self._policy_loss(j,self.observation(j))
        p.cards.remove(card); self.events.append(("lose",j,card))
        if not p.cards:
            p.alive=False
            # Eliminated players return all coins to the Treasury immediately.
            # The simulator does not need a finite Treasury balance, so zeroing
            # the public coin count is the observable equivalent.
            p.coins=0
            self.events.append(("eliminate",j))

    def _challenge(self, actor, claim, exclude=None):
        # Policies observe only their own cards, public coins/actions, and revealed cards.
        for off in range(1,len(self.players)):
            j=(actor+off)%len(self.players)
            if not self.players[j].alive or j==exclude: continue
            p=self.players[j]; obs=self.observation(j)
            if self._policy_challenge(j,claim,obs): return j
            if p.policy=="challenge_low" and claim in ("assassinate","steal") and obs["self_coins"]<2: return j
        return None

    def _block(self, actor, action, target=None):
        if action not in BLOCKS: return None
        for off in range(1,len(self.players)):
            j=(actor+off)%len(self.players)
            if not self.players[j].alive or (target is not None and j!=target): continue
            p=self.players[j]; obs=self.observation(j)
            role=self._policy_block(j,action,obs)
            if role: return j, role
        return None

    def step(self, i):
        obs=self.observation(i)
        p=self.players[i]
        if not p.alive: return
        action=self._choose_action(i,obs)
        target=self.rng.choice(self._eligible_target(i)) if action in ("coup","assassinate","steal") and self._eligible_target(i) else None
        if action=="income": p.coins+=1; return
        if action=="foreign_aid":
            if not self._block(i,action): p.coins+=2
            return
        if action=="coup": p.coins-=7; self._lose(target); return
        claim=CLAIMS.get(action)
        if action=="assassinate": p.coins-=3
        challenger=self._challenge(i,claim) if claim else None
        if challenger is not None:
            if claim in p.cards: self._lose(challenger); p.cards.remove(claim); self.deck.append(claim); self.rng.shuffle(self.deck); p.cards.append(self.deck.pop())
            else:
                if action=="assassinate": p.coins+=3
                self._lose(i)
            return
        block=self._block(i,action,target)
        if block:
            b, role=block; bc=self._challenge(i,role,exclude=b)
            if bc is not None and role in self.players[b].cards:
                self._lose(bc); self.players[b].cards.remove(role); self.deck.append(role); self.rng.shuffle(self.deck); self.players[b].cards.append(self.deck.pop()); block=None
            elif bc is not None: self._lose(b)
        if block: return
        if action=="tax": p.coins+=3
        elif action=="assassinate": self._lose(target)
        elif action=="steal":
            take=min(2,self.players[target].coins); self.players[target].coins-=take; p.coins+=take
        elif action=="exchange":
            drawn=[self.deck.pop() for _ in range(2)]; pool=p.cards+drawn; p.cards=[]
            chosen=self.rng.sample(range(len(pool)), min(2,len(pool)))
            p.cards=[pool[k] for k in chosen]
            self.deck.extend(pool[k] for k in range(len(pool)) if k not in chosen); self.rng.shuffle(self.deck)

    def run(self):
        i=0
        while len(self.alive())>1 and self.turn<self.max_turns:
            if self.players[i].alive: self.step(i)
            self.turn+=1; i=(i+1)%len(self.players)
        return self.alive()[0] if len(self.alive())==1 else None

def experiment(games=10000, players=4, seed=20261010, policies=None):
    wins=Counter()
    for k in range(games):
        ps=policies or ["baseline"]*players
        w=Game(players,seed+k,ps).run()
        if w is not None: wins[ps[w]]+=1
    return {p: wins[p]/games for p in sorted(set(policies or ["baseline"]))}, sum(wins.values())/games

if __name__ == '__main__':
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('-n','--players',type=int,default=4); ap.add_argument('-g','--games',type=int,default=10000); ap.add_argument('--seed',type=int,default=20261010); a=ap.parse_args()
    print(experiment(a.games,a.players,a.seed,["baseline"]*a.players))
