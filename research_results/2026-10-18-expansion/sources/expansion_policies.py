"""Finite public-information policies for the separate expansion study."""
from __future__ import annotations

import math
from collections import Counter

CONFIGS = {
    'honest': dict(survival_bluff=False, bluff=0., block_bluff=0., challenge='impossible', treasury=1., shield=0., convert=0., information=.5, defense=1., coup_at=7),
    'bluff': dict(tax_only=True, bluff=1., block_bluff=1., challenge='impossible', treasury=0., shield=0., convert=0., information=0., defense=1., coup_at=7),
    'skeptic': dict(bluff=0., block_bluff=.1, challenge='always', treasury=1., shield=.4, convert=.3, information=.7, defense=1., coup_at=7),
    'treasury': dict(bluff=.25, block_bluff=.25, challenge='selective', treasury=1.8, shield=.6, convert=.6, information=.5, defense=1., coup_at=7),
    'shield': dict(bluff=.05, block_bluff=.1, challenge='cautious', treasury=1., shield=2., convert=.4, information=.5, defense=1.8, coup_at=8),
    'converter': dict(bluff=.2, block_bluff=.2, challenge='selective', treasury=1.1, shield=1.5, convert=2., information=.6, defense=1.2, coup_at=7),
    'information': dict(bluff=.1, block_bluff=.15, challenge='selective', treasury=1., shield=.6, convert=.5, information=1.8, defense=1., coup_at=8),
    'balanced': dict(bluff=.2, block_bluff=.25, challenge='selective', treasury=1.2, shield=1., convert=1., information=1.1, defense=1.2, coup_at=7),
}
LABELS = {'honest':'Truthful economy','bluff':'Tax bluffer','skeptic':'Always challenge','treasury':'Treasury seeker','shield':'Defensive conversion','converter':'Active conversion','information':'Information seeker','balanced':'Balanced'}
DESCRIPTIONS = {
    'honest':'Claims held roles, challenges impossible claims, collects the reserve when not holding Duke, and Coups at seven coins.',
    'bluff':'Claims Tax on non-Coup turns and attempts every legal block, including bluffs. Coups at seven coins.',
    'skeptic':'Challenges every role claim, uses held-role actions and sometimes bluffs a block. Coups at seven coins.',
    'treasury':'Prioritizes larger reserve withdrawals, permits some action and block bluffs, and uses selective challenges. Coups at seven coins.',
    'shield':'Prioritizes conversion when it protects against a visible coin threat, keeps defensive cards, and bluffs rarely. Usually Coups at eight coins.',
    'converter':'Gives conversion more weight when it reduces immediate threats; also uses the reserve and selective challenges. Coups at seven coins.',
    'information':'Values exchanges and examinations, uses still-valid private inspections when challenging, and makes occasional bluffs. Usually Coups at eight coins.',
    'balanced':'Balances reserve income, threat-aware conversion, card retention, examination and selective challenges. Coups at seven coins.',
}


def role_probability(view, player, role):
    """Uniform unseen-card prior, adjusted only by this observer's valid inspection."""
    own = view['own_cards']
    public = view['players']
    remaining = view['copies'] - own.count(role) - sum(p[3].count(role) for p in public)
    unknown = len(view['roles']) * view['copies'] - len(own) - sum(len(p[3]) for p in public)
    count = public[player][1]
    known = dict(view['inspected']).get(player)
    if known == role:
        return 1.
    if known is not None:
        unknown -= 1
        count -= 1
    if count <= 0 or remaining <= 0:
        return 0.
    if remaining >= unknown or unknown - remaining < count:
        return 1.
    return 1. - math.comb(unknown - remaining, count) / math.comb(unknown, count)


def card_value(view, role, config):
    i = view['self']; public = view['players']; coins = public[i][0]
    threats = any(j != i and p[1] and p[0] >= 3 for j, p in enumerate(public))
    return {'duke':3.2 if coins < 7 else 2., 'captain':2.3, 'assassin':2.6 if coins >= 3 else 1.3,
            'contessa':(2.2 if threats else 1.) * config['defense'],
            'ambassador':1.1 * config['information'], 'inquisitor':1.6 * config['information']}[role]


def keep_indices(view, pool, count, rng, config):
    selected = []; seen = Counter()
    for _ in range(count):
        choices = [j for j in range(len(pool)) if j not in selected]
        j = max(choices, key=lambda k:(card_value(view,pool[k],config)-.6*seen[pool[k]],-k))
        selected.append(j); seen[pool[j]] += 1
    return selected


def discard_index(view, rng, config):
    return min(range(len(view['own_cards'])), key=lambda k:(card_value(view,view['own_cards'][k],config),k))


def show_index(view, inspector, rng, config):
    return discard_index(view,rng,config)


def force_replace(view, target, shown, rng, config):
    # A kept card remains privately known until that hand next changes.
    return shown in ('duke','captain','assassin') or (shown=='contessa' and view['players'][target][1]==1)


def wants_challenge(view, claimant, role, negative, rng, config):
    p = role_probability(view,claimant,role)
    if negative:
        p = 1.-p
    if p <= 0:
        return True
    if config['challenge'] == 'always':
        return True
    if p >= 1 or config['challenge']=='impossible':
        return False
    successes, failures = view['claim_history'][claimant]
    reliability = (3 + successes) / (5 + successes + failures)
    credibility = p + (1-p)*reliability
    threshold = .55 if config['challenge']=='selective' else .3
    if view['players'][view['self']][1] == 1:
        threshold -= .2
    action = view['current_action']
    if action and action[1]=='assassinate' and action[2]==view['self']:
        threshold += .25
    if negative and view['pending_embezzle'] and view['pending_embezzle'][1] >= 5:
        threshold += .1
    return credibility < threshold


def choose_block(view, action, actor, rng, config):
    roles = {'foreign_aid':('duke',),'assassinate':('contessa',),
             'steal':('captain','inquisitor' if 'inquisitor' in view['roles'] else 'ambassador')}.get(action,())
    held = next((r for r in roles if r in view['own_cards']),None)
    if held:
        return held
    if roles and (rng.random() < config['block_bluff'] or (config.get('survival_bluff',True) and action=='assassinate' and view['players'][view['self']][1]==1)):
        return roles[0]
    return None


def choose_action(view, rng, config):
    legal = view['legal_actions']; i=view['self']; public=view['players']; coins=public[i][0]
    coups=[a for a in legal if a[0]=='coup']
    def threat(j):
        p=public[j]
        return p[0]+5*(p[1]==1)
    if coups and coins >= config['coup_at']:
        return max(coups,key=lambda a:(threat(a[1]),-a[1]))
    if config.get('tax_only',False):
        return ('tax',None)
    pressure=min(.9,(view['challenge_count']+1)/(view['claim_count']+6))
    own=view['own_cards']; n_alive=sum(p[1]>0 for p in public)
    probabilities={}
    def prob(j,role):
        key=(j,role)
        if key not in probabilities:probabilities[key]=role_probability(view,j,role)
        return probabilities[key]
    def allowed_claim(role):return role in own or rng.random()<config['bluff']
    def claim_penalty(role):return 0. if role in own else pressure*(3.5 if len(own)==1 else 2.5)
    scores=[]
    for kind,target in legal:
        score=-100.
        if kind=='income':score=1.
        elif kind=='foreign_aid':
            blockers=view['aid_blockers']; block=sum(prob(j,'duke') for j in blockers)
            score=2.*max(.15,1.-.65*min(1.,block))
        elif kind=='tax' and allowed_claim('duke'):score=3.-claim_penalty('duke')
        elif kind=='steal' and allowed_claim('captain'):
            blocking='inquisitor' if 'inquisitor' in view['roles'] else 'ambassador'
            score=min(2,public[target][0])*(1.-.4*min(1.,prob(target,'captain')+prob(target,blocking)))+.08*threat(target)-claim_penalty('captain')
        elif kind=='assassinate' and allowed_claim('assassin'):
            score=(6.5+2.*(public[target][1]==1))*(1.-.65*prob(target,'contessa'))-1.5-claim_penalty('assassin')
        elif kind=='coup':score=6.+.1*threat(target)
        elif kind=='exchange':
            role='inquisitor' if 'inquisitor' in view['roles'] else 'ambassador'
            if role in own:score=(1.2+(1. if 'duke' not in own else 0.))*config['information']
        elif kind=='examine' and allowed_claim('inquisitor'):
            score=config['information']*(1.2+.15*threat(target))-.5*claim_penalty('inquisitor')
        elif kind=='embezzle':
            if 'duke' not in own or rng.random()<config['bluff']:
                score=view['treasury']*config['treasury']-(pressure*5 if 'duke' in own else 0.)
        elif kind in ('convert_self','convert_other'):
            factions=[p[2] for p in public]
            if kind=='convert_self':factions[i]=1-factions[i]
            else:factions[target]=1-factions[target]
            active={factions[j] for j,p in enumerate(public) if p[1]}
            if len(active)>1:
                before=sum(max(0.,p[0]-4)*(2. if len(own)==1 else 1.) for j,p in enumerate(public) if j!=i and p[1] and p[2]!=public[i][2])
                after=sum(max(0.,p[0]-4)*(2. if len(own)==1 else 1.) for j,p in enumerate(public) if j!=i and p[1] and factions[j]!=factions[i])
                score=(before-after)*config['shield']+.25*config['convert']-(1 if kind=='convert_self' else 2)
        scores.append((score+rng.random()*.12,kind,target))
    _,kind,target=max(scores,key=lambda x:x[0])
    return kind,target
