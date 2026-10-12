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
    def test_action_policy_receives_observation(self):
        g=Game(3,2,["baseline"]*3); seen=[]; original=g._choose_action
        def wrapped(i, obs): seen.append((i,obs)); return original(i,obs)
        g._choose_action=wrapped; g.step(1)
        self.assertEqual(seen[0][0],1); self.assertIn("self_cards",seen[0][1])
    def test_clockwise_challenge_starts_after_actor(self):
        g=Game(4,2); order=[]
        original=g.observation
        def wrapped(i): order.append(i); return original(i)
        g.observation=wrapped; g.players[2].policy="challenge_heavy"; g.step(1)
        self.assertIn(2,order)
    def test_duplicate_exchange_conserves_cards_with_one_influence(self):
        g=Game(3,3,["exchange","baseline","baseline"]); g.players[0].cards=["duke"]
        before=len(g.deck)+sum(len(p.cards) for p in g.players); g.step(0)
        self.assertEqual(before,len(g.deck)+sum(len(p.cards) for p in g.players))
    def test_duplicate_policy_labels_preserve_identity(self):
        from benchmark_policies import focal_index_for
        self.assertEqual(focal_index_for(4,0,1),1)
        self.assertEqual(focal_index_for(4,1,1),2)
    def test_ambassador_and_captain_can_each_block_steal(self):
        g=Game(3,4,["captain","baseline","baseline"])
        self.assertEqual(g._policy_block(1,"steal",{"self_cards":("ambassador",)}),"ambassador")
        self.assertEqual(g._policy_block(1,"steal",{"self_cards":("captain",)}),"captain")
    def test_ambassador_block_survives_challenge_integration(self):
        g=Game(3,7,["captain","baseline","challenge_heavy"])
        g.players[0].coins=2; g.players[0].cards=["captain","duke"]; g.players[1].cards=["ambassador","duke"]
        g._choose_action=lambda i,obs: "steal" if i==0 else "income"
        g._eligible_target=lambda i: [1] if i==0 else []
        before=g.players[1].influence(); g.step(0)
        self.assertEqual(g.players[1].influence(),before)
    def test_captain_block_survives_challenge_integration(self):
        g=Game(3,8,["captain","baseline","challenge_heavy"])
        g.players[0].coins=2; g.players[0].cards=["captain","duke"]; g.players[1].cards=["captain","duke"]
        g._choose_action=lambda i,obs: "steal" if i==0 else "income"
        g._eligible_target=lambda i: [1] if i==0 else []
        before=g.players[1].influence(); g.step(0)
        self.assertEqual(g.players[1].influence(),before)
    def test_baseline_challenges_publicly_impossible_claim(self):
        g=Game(3,4); g.events=[("lose",1,"duke"),("lose",2,"duke"),("lose",1,"duke")]
        self.assertTrue(g._policy_challenge(0,"duke",g.observation(0)))
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
        g._challenge=lambda actor, claim, exclude=None: None; g._block=lambda actor, action, target=None: (1,"contessa"); g.step(0)
        self.assertEqual(g.players[0].coins,2)

    def test_assassination_challenge_refunds_fee(self):
        g=Game(3,1,["assassin","challenge_aggressive","baseline"]); g.players[0].coins=5; g.players[0].cards=["duke","captain"]
        g._block=lambda actor, action, target=None: None; g.step(0)
        self.assertEqual(g.players[0].coins,5)

    def test_elimination_returns_coins(self):
        g=Game(3,1); g.players[1].coins=4; g.players[1].cards=["duke"]
        g._lose(1)
        self.assertFalse(g.players[1].alive); self.assertEqual(g.players[1].coins,0)

if __name__=='__main__': unittest.main()
