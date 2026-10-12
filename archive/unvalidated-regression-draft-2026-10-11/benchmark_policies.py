from coup_simulator import Game
from run_experiments import trial

def focal_index_for(players, focal_original_seat, rotation):
    ids=list(range(players)); rotated_ids=ids[-rotation:]+ids[:-rotation] if rotation else ids
    return rotated_ids.index(focal_original_seat)

def table(players, policies, games=1000, seed=20261101):
    out=[]
    for seat, focal in enumerate(policies):
        wins=draws=0
        rotated=policies[-seat:]+policies[:-seat] if seat else policies
        focal_index=focal_index_for(players,seat,seat)
        for k in range(games):
            w=Game(players,seed+seat*100000+k,rotated).run()
            if w is None: draws+=1
            elif w==focal_index: wins+=1
        denom=games-draws; p=wins/denom if denom else 0; z=1.96; d=1+z*z/denom if denom else 1
        c=(p+z*z/(2*denom))/d if denom else 0; h=z*((p*(1-p)/denom+z*z/(4*denom*denom))**.5)/d if denom else 0
        lo,hi=max(0,c-h),min(1,c+h)
        out.append((players,seat,focal,wins,denom,draws,round(lo,4),round(hi,4)))
    return out

if __name__=='__main__':
    print('players,seat,policy,wins,denominator,draws,lower95,upper95')
    for n in (2,3,4,5,6):
        for policies in (["baseline"]*n,["bluff_heavy"]*n,["challenge_heavy"]*n,["bluff_heavy","challenge_heavy"]+["baseline"]*(n-2)):
            for row in table(n,policies): print(','.join(map(str,row)))
