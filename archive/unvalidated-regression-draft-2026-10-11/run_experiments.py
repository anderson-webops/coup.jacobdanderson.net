"""Small reproducible balanced-seat experiment runner."""
from coup_simulator import Game
from math import sqrt

def trial(n, policy, games, seed, seat):
    ps=[policy]+["baseline"]*(n-1); wins=draws=0
    rotated=ps[-seat:]+ps[:-seat] if seat else ps
    for k in range(games):
        w=Game(n,seed+k,rotated).run()
        if w is None: draws+=1
        elif rotated[w]==policy: wins+=1
    denom=games-draws; p=wins/denom if denom else 0
    # Wilson 95% interval; seat means are reported separately because seats
    # are correlated blocks, not treated as independent games.
    z=1.96; d=1+z*z/denom if denom else 1; c=(p+z*z/(2*denom))/d if denom else 0
    h=z*sqrt(p*(1-p)/denom+z*z/(4*denom*denom))/d if denom else 0
    return wins,denom,draws,max(0,c-h),min(1,c+h)

def balanced(n, games, seed):
    names=("baseline","taxer","captain","foreign_aid")
    rows=[]
    for focal in names:
        ps=[focal]+["baseline"]*(n-1)
        shares=[]
        for seat in range(n):
            rotated=ps[-seat:]+ps[:-seat] if seat else ps
            wins,denom,draws,lo,hi=trial(n,focal,games,seed+seat*100000,seat)
            shares.append((wins,denom,draws,lo,hi))
        rows.append((n,focal,shares))
    return rows

if __name__=='__main__':
    print('players,policy,seat,wins,denominator,draws,lower95,upper95')
    for n in (3,4,5,6):
        for players,policy,rows in balanced(n,1000,20261010):
            for seat,row in enumerate(rows): print(','.join(map(str,(players,policy,seat)+row)))
