import unittest
from coup_simulator import Game, ROLES, experiment

class RulesTests(unittest.TestCase):
    def test_deck_and_setup(self):
        g=Game(4,1); self.assertEqual(sum(len(p.cards) for p in g.players)+len(g.deck),15); self.assertEqual([p.coins for p in g.players],[2]*4)
    def test_invalid_players(self):
        with self.assertRaises(ValueError): Game(1)
        with self.assertRaises(ValueError): Game(7)
    def test_two_player_starting_coin_rule(self):
        g=Game(2,1); self.assertEqual([p.coins for p in g.players],[1,2])
    def test_observation_hides_opponents_and_deck(self):
        g=Game(4,1); a=g.observation(0); g.players[1].cards.reverse(); g.deck.reverse()
        self.assertEqual(a,g.observation(0))
        self.assertNotIn("deck",a); self.assertNotIn("opponent_cards",a)
    def test_engine_uses_observation_boundary(self):
        g=Game(3,2,["bluff_heavy"]*3); seen=[]; original=g.observation
        def wrapped(i): seen.append(i); return original(i)
        g.observation=wrapped; g.step(0)
        self.assertIn(0,seen)
    def test_deterministic(self):
        self.assertEqual(Game(4,9).run(),Game(4,9).run())
    def test_termination(self):
        self.assertIsNotNone(Game(3,4,max_turns=1000).run())
    def test_experiment(self):
        x, completed=experiment(100,3,8); self.assertAlmostEqual(completed,1.0)

    def test_assassination_fee_is_spent_on_block(self):
        g=Game(3,1,["assassin"]*3); g.players[0].coins=5; g.players[0].cards=["assassin","duke"]; g.players[1].cards=["contessa","duke"]
        g._challenger=lambda claimant, role: None; g._block=lambda actor, action, target=None: (1,"contessa"); g.step(0)
        self.assertEqual(g.players[0].coins,2)

    def test_assassination_challenge_refunds_fee(self):
        g=Game(3,1,["assassin","challenge_aggressive","baseline"]); g.players[0].coins=5; g.players[0].cards=["duke","captain"]
        g._block=lambda actor, action, target=None: None; g.step(0)
        self.assertEqual(g.players[0].coins,5)

    def test_elimination_returns_coins(self):
        g=Game(3,1); g.players[1].coins=4; g.players[1].cards=["duke"]
        g._lose(1)
        self.assertFalse(g.players[1].alive); self.assertEqual(g.players[1].coins,0)

    def test_truthful_tax_challenge_still_pays_tax(self):
        g=Game(3,1,["baseline","challenge_heavy","baseline"])
        g.players[0].cards=["duke","captain"]
        g._choose_action=lambda _: "tax"
        g.step(0)
        self.assertEqual(g.players[0].coins,5)
        self.assertEqual(g.players[1].influence(),1)

    def test_truthful_assassin_challenged_by_target_can_cost_two_influence(self):
        g=Game(3,1,["assassin","challenge_heavy","baseline"])
        g.players[0].cards=["assassin","duke"]
        g.players[0].coins=5
        g.players[1].cards=["captain","ambassador"]
        g._target=lambda *_: 1
        g.step(0)
        self.assertFalse(g.players[1].alive)
        self.assertEqual(g.players[0].coins,2)

    def test_truthful_challenged_contessa_block_stands(self):
        g=Game(3,1,["challenge_heavy","baseline","baseline"])
        g.players[0].cards=["assassin","duke"]
        g.players[0].coins=5
        g.players[1].cards=["contessa","captain"]
        g._choose_action=lambda _: "assassinate"
        g._target=lambda *_: 1
        g._challenger=lambda claimant, role: 0 if claimant==1 else None
        g.step(0)
        self.assertEqual(g.players[1].influence(),2)
        self.assertEqual(g.players[0].influence(),1)
        self.assertEqual(g.players[0].coins,2)

    def test_false_challenged_contessa_block_fails(self):
        g=Game(3,1,["challenge_heavy","block_aggressive","baseline"])
        g.players[0].cards=["assassin","duke"]
        g.players[0].coins=5
        g.players[1].cards=["captain","ambassador"]
        g._choose_action=lambda _: "assassinate"
        g._target=lambda *_: 1
        g._challenger=lambda claimant, role: 0 if claimant==1 else None
        g.step(0)
        self.assertFalse(g.players[1].alive)
        self.assertEqual(g.players[0].coins,2)

    def test_foreign_aid_block_may_be_challenged_by_actor(self):
        g=Game(3,1,["challenge_heavy","block_aggressive","baseline"])
        g.players[1].cards=["contessa","captain"]
        g._choose_action=lambda _: "foreign_aid"
        g.step(0)
        self.assertIn(("challenge",0,1,"duke"),g.events)
        self.assertEqual(g.players[0].coins,4)

    def test_foreign_aid_block_may_be_challenged_by_third_party(self):
        g=Game(3,1,["baseline","block_aggressive","challenge_heavy"])
        g.players[1].cards=["contessa","captain"]
        g._choose_action=lambda _: "foreign_aid"
        g.step(0)
        self.assertIn(("challenge",2,1,"duke"),g.events)
        self.assertEqual(g.players[0].coins,4)

    def test_ambassador_blocks_steal(self):
        g=Game(3,1)
        g.players[1].cards=["ambassador","contessa"]
        self.assertEqual(g._block(0,"steal",1),(1,"ambassador"))

    def test_one_influence_exchange_keeps_one_card(self):
        g=Game(3,1)
        g._lose(0)
        g._exchange(0)
        self.assertEqual(g.players[0].influence(),1)
        g.assert_valid_state()

    def test_exchange_conserves_duplicate_roles(self):
        for seed in range(50):
            g=Game(3,seed)
            g._exchange(0)
            g.assert_valid_state()

    def test_baseline_claims_only_cards_it_holds(self):
        from coup_simulator import CLAIMS
        for seed in range(100):
            g=Game(3,seed)
            action=g._choose_action(0)
            if action in CLAIMS:
                self.assertIn(CLAIMS[action],g.players[0].cards)

    def test_blocker_cannot_challenge_own_claim(self):
        g=Game(3,1,["baseline","challenge_heavy","baseline"])
        self.assertNotEqual(g._challenger(1,"duke"),1)

    def test_false_assassin_eliminated_by_challenge_returns_all_coins(self):
        g=Game(3,1,["assassin","challenge_heavy","baseline"])
        g.players[0].cards=["contessa"]
        g.players[0].coins=4
        g.step(0)
        self.assertFalse(g.players[0].alive)
        self.assertEqual(g.players[0].coins,0)

    def test_randomized_games_conserve_cards_and_influence(self):
        from coup_simulator import POLICIES
        from random import Random
        rng=Random(7)
        for n in range(2,7):
            for seed in range(40):
                names=[rng.choice(POLICIES) for _ in range(n)]
                g=Game(n,100000*n+seed,names)
                i=0
                while len(g.alive())>1 and g.turn<g.max_turns:
                    if g.players[i].alive:
                        g.step(i)
                        g.turn+=1
                    g.assert_valid_state()
                    i=(i+1)%n
    def test_rotated_focal_identity(self):
        from run_experiments import roster
        for n in range(2,7):
            for seat in range(n):
                for game in range(3):
                    self.assertEqual(roster(n,"income","mixed",seat,game)[seat],"income")

if __name__=='__main__': unittest.main()
