"""Separate Coup: Reformation/Inquisitor engine; no frozen base-study imports."""
from __future__ import annotations

import hashlib
import random
from collections import Counter
from dataclasses import dataclass,field
import expansion_policies as policies_module

PROFILES=('inquisitor','reformation','combined')
BASE_ROLES=('duke','assassin','captain','ambassador','contessa')


@dataclass(frozen=True)
class Action:
    kind:str
    target:int|None=None


@dataclass
class Player:
    cards:list[str]
    coins:int=2
    allegiance:int=0
    exposed:list[str]=field(default_factory=list)

    @property
    def alive(self):return bool(self.cards)
    def influence(self):return len(self.cards)


class ExpansionGame:
    def __init__(self,n,seed,policies,profile='combined',max_turns=1000,strict=True,record=False,identities=None):
        if not isinstance(n,int) or isinstance(n,bool) or not 2<=n<=10:raise ValueError('players must be 2–10')
        if profile not in PROFILES:raise ValueError('unknown expansion profile')
        if len(policies)!=n or any(p not in policies_module.CONFIGS for p in policies):raise ValueError('unknown policy or roster size')
        identities=list(range(n)) if identities is None else list(identities)
        if sorted(identities)!=list(range(n)):raise ValueError('identities must be a seat permutation')
        if not isinstance(max_turns,int) or max_turns<1:raise ValueError('invalid turn cap')
        self.n=n;self.profile=profile;self.policy_names=tuple(policies);self.identities=identities
        self.roles=tuple('inquisitor' if r=='ambassador' and profile!='reformation' else r for r in BASE_ROLES)
        self.copies=3 if n<=6 else 4 if n<=8 else 5
        self.rng=random.Random(seed)
        self.decision_rngs=[random.Random(int.from_bytes(hashlib.sha256(f'{seed}:decision:{identity}'.encode()).digest()[:16],'big')) for identity in identities]
        self.deck=[r for r in self.roles for _ in range(self.copies)];self.rng.shuffle(self.deck)
        self.players=[Player([self.deck.pop(),self.deck.pop()],1 if n==2 and i==0 else 2,i%2) for i in range(n)]
        self.treasury=0;self.bank_net=sum(p.coins for p in self.players)
        self.max_turns=max_turns;self.turn=0;self.strict=strict;self.record=record
        self.epochs=[0]*n;self.private_knowledge=[{} for _ in range(n)]
        self.claim_success=[0]*n;self.claim_failure=[0]*n
        self.claim_count=0;self.challenge_count=0;self.current_action=None;self.pending_embezzle=None;self.public_proof=()
        self.events=[];self.diagnostics=Counter()
        self.check_invariants()

    def alive(self):return [i for i,p in enumerate(self.players) if p.alive]
    def _log(self,kind,*args):
        self.diagnostics[kind]+=1
        if self.record:self.events.append((kind,*args))
    def _config(self,i):return policies_module.CONFIGS[self.policy_names[i]]
    def _factions_active(self):return self.profile!='inquisitor' and len({p.allegiance for p in self.players if p.alive})>1
    def eligible_target(self,i,j,kind):
        if not 0<=i<self.n or not 0<=j<self.n or i==j or not self.players[i].alive or not self.players[j].alive:return False
        restricted=kind in ('coup','assassinate','steal','examine','foreign_aid')
        return not(restricted and self._factions_active() and self.players[i].allegiance==self.players[j].allegiance)

    def available_actions(self,i):
        if not 0<=i<self.n or not self.players[i].alive:return ()
        live=[j for j,p in enumerate(self.players) if p.alive]
        if len(live)<2:return ()
        coins=self.players[i].coins
        restricted=self._factions_active()
        targets=[j for j in live if j!=i and (not restricted or self.players[j].allegiance!=self.players[i].allegiance)]
        coups=[Action('coup',j) for j in targets] if coins>=7 else []
        if coins>=10:return tuple(coups)
        actions=[Action('income'),Action('foreign_aid'),Action('tax'),Action('exchange')]+coups
        for j in targets:
            actions.append(Action('steal',j))
            if coins>=3:actions.append(Action('assassinate',j))
            if 'inquisitor' in self.roles:actions.append(Action('examine',j))
        if self.profile!='inquisitor':
            actions.append(Action('embezzle'))
            if coins>=1:actions.append(Action('convert_self'))
            if coins>=2:actions.extend(Action('convert_other',j) for j in live if j!=i)
        return tuple(actions)

    def observation(self,i,include_actions=True):
        public=tuple((p.coins,len(p.cards),p.allegiance,tuple(p.exposed)) for p in self.players)
        seen=tuple(sorted((j,r) for j,(r,epoch) in self.private_knowledge[i].items() if epoch==self.epochs[j] and self.players[j].alive))
        return {'self':i,'own_cards':tuple(self.players[i].cards),'players':public,'roles':self.roles,'copies':self.copies,
                'profile':self.profile,'treasury':self.treasury,'inspected':seen,'claim_history':tuple(zip(self.claim_success,self.claim_failure)),
                'challenge_count':self.challenge_count,'claim_count':self.claim_count,'current_action':self.current_action,
                'pending_embezzle':self.pending_embezzle,'public_proof':self.public_proof,
                'legal_actions':tuple((a.kind,a.target) for a in self.available_actions(i)) if include_actions else (),
                'aid_blockers':tuple(j for j in range(self.n) if self.eligible_target(i,j,'foreign_aid')) if include_actions else ()}

    def _hand_changed(self,i):
        self.epochs[i]+=1
        for knowledge in self.private_knowledge:knowledge.pop(i,None)

    def _lose(self,i):
        p=self.players[i]
        if not p.alive:return
        index=policies_module.discard_index(self.observation(i,False),self.decision_rngs[i],self._config(i))
        if not isinstance(index,int) or not 0<=index<len(p.cards):raise ValueError('invalid influence-loss choice')
        role=p.cards.pop(index);p.exposed.append(role);self._hand_changed(i);self._log('influence_loss',i,role)
        if not p.alive:
            self.bank_net-=p.coins;p.coins=0;self._log('elimination',i)

    def _replace_proof(self,i,cards):
        p=self.players[i]
        for role in cards:p.cards.remove(role)
        self.deck.extend(cards);self.rng.shuffle(self.deck)
        p.cards.extend(self.deck.pop() for _ in cards);self._hand_changed(i)

    def resolve_claim(self,claimant,role,challenger,negative=False,concede=False):
        if role not in self.roles or claimant==challenger or not self.players[claimant].alive or not self.players[challenger].alive:raise ValueError('invalid challenge')
        if negative and role!='duke':raise ValueError('only Duke has a negative claim')
        self.challenge_count+=1;self._log('challenge',challenger,claimant,role,negative)
        held=role in self.players[claimant].cards
        truthful=(not held) if negative else held
        if truthful and not concede:
            cards=list(self.players[claimant].cards) if negative else [role]
            self.public_proof=((claimant,tuple(cards)),)
            self._log('proof',claimant,tuple(cards));self.claim_success[claimant]+=1
            self._lose(challenger)
            self._replace_proof(claimant,cards)
            self.public_proof=()
            return True
        if negative and self.pending_embezzle and self.pending_embezzle[0]==claimant:
            amount=self.pending_embezzle[1]
            self.players[claimant].coins-=amount;self.treasury+=amount;self.pending_embezzle=None
        self.claim_failure[claimant]+=1;self._log('disproved',claimant,role,negative);self._lose(claimant)
        return False

    def _challenger(self,claimant,role,negative=False):
        for offset in range(1,self.n):
            j=(claimant+offset)%self.n
            if self.players[j].alive and policies_module.wants_challenge(self.observation(j,False),claimant,role,negative,self.decision_rngs[j],self._config(j)):return j
        return None

    def _claim_stands(self,claimant,role,negative=False):
        self.claim_count+=1;self._log('claim',claimant,role,negative)
        challenger=self._challenger(claimant,role,negative)
        return True if challenger is None else self.resolve_claim(claimant,role,challenger,negative)

    def _block(self,actor,action,target):
        if action not in ('foreign_aid','steal','assassinate'):return None
        for offset in range(1,self.n):
            j=(actor+offset)%self.n
            if not self.players[j].alive:continue
            if action=='foreign_aid':
                if not self.eligible_target(actor,j,'foreign_aid'):continue
            elif j!=target:continue
            role=policies_module.choose_block(self.observation(j,False),action,actor,self.decision_rngs[j],self._config(j))
            if role:
                allowed={'foreign_aid':('duke',),'steal':('captain','inquisitor' if 'inquisitor' in self.roles else 'ambassador'),'assassinate':('contessa',)}[action]
                if role not in allowed:raise ValueError('invalid block claim')
                return j,role
        return None

    def _exchange(self,i,draw_count):
        p=self.players[i];count=len(p.cards)
        drawn=[self.deck.pop() for _ in range(draw_count)];pool=p.cards+drawn
        indices=policies_module.keep_indices(self.observation(i,False),tuple(pool),count,self.decision_rngs[i],self._config(i))
        if len(indices)!=count or len(set(indices))!=count or any(not isinstance(j,int) or not 0<=j<len(pool) for j in indices):raise ValueError('invalid exchange keep')
        selected=set(indices);p.cards=[r for j,r in enumerate(pool) if j in selected]
        self.deck.extend(r for j,r in enumerate(pool) if j not in selected);self.rng.shuffle(self.deck)
        self._hand_changed(i);self._log('exchange',i,draw_count)

    def _examine(self,i,target):
        if not self.players[target].alive:return
        p=self.players[target]
        index=policies_module.show_index(self.observation(target,False),i,self.decision_rngs[target],self._config(target))
        if not isinstance(index,int) or not 0<=index<len(p.cards):raise ValueError('invalid examination card')
        shown=p.cards[index]
        replace=policies_module.force_replace(self.observation(i,False),target,shown,self.decision_rngs[i],self._config(i))
        self._log('examine',i,target,'replace' if replace else 'keep')
        if replace:
            replacement=self.deck.pop()  # shown card cannot be drawn in its own replacement
            p.cards[index]=replacement;self.deck.append(shown);self.rng.shuffle(self.deck);self._hand_changed(target)
        else:self.private_knowledge[i][target]=(shown,self.epochs[target])

    def step(self,i,action=None):
        if not self.players[i].alive:return
        if action is None:action=Action(*policies_module.choose_action(self.observation(i),self.decision_rngs[i],self._config(i)))
        elif isinstance(action,tuple):action=Action(*action)
        if action not in self.available_actions(i):raise ValueError(f'illegal action: {action}')
        p=self.players[i];kind=action.kind;target=action.target
        self.current_action=(i,kind,target);self._log('action_'+kind,i,target)
        if self.identities[i]==0:self.diagnostics['focal_'+kind]+=1
        if kind=='income':p.coins+=1;self.bank_net+=1
        elif kind=='coup':p.coins-=7;self.bank_net-=7;self._lose(target)
        elif kind in ('convert_self','convert_other'):
            cost=1 if kind=='convert_self' else 2;p.coins-=cost;self.treasury+=cost
            j=i if kind=='convert_self' else target;self.players[j].allegiance=1-self.players[j].allegiance
        elif kind=='embezzle':
            amount=self.treasury;self.treasury=0;p.coins+=amount;self.pending_embezzle=(i,amount)
            self._claim_stands(i,'duke',True);self.pending_embezzle=None
        else:
            if kind=='assassinate':p.coins-=3;self.bank_net-=3
            role={'tax':'duke','steal':'captain','assassinate':'assassin','exchange':'inquisitor' if 'inquisitor' in self.roles else 'ambassador','examine':'inquisitor'}.get(kind)
            if role and not self._claim_stands(i,role):
                if kind=='assassinate' and p.alive:p.coins+=3;self.bank_net+=3
            elif p.alive:
                block=self._block(i,kind,target)
                blocked=False
                if block:
                    blocker,block_role=block;self._log('block',blocker,block_role,kind)
                    blocked=self._claim_stands(blocker,block_role)
                if not blocked:
                    if kind=='foreign_aid':p.coins+=2;self.bank_net+=2
                    elif kind=='tax':p.coins+=3;self.bank_net+=3
                    elif kind=='steal' and self.players[target].alive:
                        amount=min(2,self.players[target].coins);self.players[target].coins-=amount;p.coins+=amount
                    elif kind=='assassinate':self._lose(target)
                    elif kind=='exchange':self._exchange(i,1 if 'inquisitor' in self.roles else 2)
                    elif kind=='examine':self._examine(i,target)
        self.current_action=None
        if self.strict:self.check_invariants()

    def check_invariants(self):
        cards=list(self.deck)
        for p in self.players:
            if not 0<=len(p.cards)<=2 or len(p.cards)+len(p.exposed)!=2:raise ValueError('influence count changed')
            if not isinstance(p.coins,int) or p.coins<0 or (not p.alive and p.coins):raise ValueError('invalid player coins')
            if p.allegiance not in (0,1):raise ValueError('invalid allegiance')
            cards.extend(p.cards);cards.extend(p.exposed)
        if Counter(cards)!=Counter({r:self.copies for r in self.roles}):raise ValueError('card conservation failed')
        if not isinstance(self.treasury,int) or self.treasury<0 or sum(p.coins for p in self.players)+self.treasury!=self.bank_net:raise ValueError('coin conservation failed')
        return True

    def run(self):
        i=0
        while len(self.alive())>1 and self.turn<self.max_turns:
            if self.players[i].alive:self.step(i);self.turn+=1
            i=(i+1)%self.n
        alive=self.alive()
        return alive[0] if len(alive)==1 else None
