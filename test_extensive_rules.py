"""Independent outcome tests for the frozen standard Coup engine.

Fixtures account for all 15 physical role cards. Policy choices are replaced
only when a specific legal action is needed to exercise a rule transition.
"""

from collections import Counter
from contextlib import ExitStack
from random import Random
from unittest import TestCase, main
from unittest.mock import patch

from coup_simulator import CLAIMS, POLICIES, ROLES, Game, experiment


def arranged(hands, *, revealed=None, coins=None, policies=None, seed=17, max_turns=1000):
    """Build a possible state with each player's two cards accounted for."""
    n = len(hands)
    exposed = revealed if revealed is not None else [()] * n
    if len(exposed) != n or any(len(hand) + len(turned) != 2 for hand, turned in zip(hands, exposed)):
        raise ValueError("each player must have exactly two face-down or revealed cards")
    if coins is not None and len(coins) != n:
        raise ValueError("one coin count per player is required")
    used = Counter(role for group in list(hands) + list(exposed) for role in group)
    if any(role not in ROLES for role in used) or any(used[role] > 3 for role in ROLES):
        raise ValueError("fixture exceeds the three copies of a role")

    game = Game(n, seed, policies=policies, max_turns=max_turns)
    for i, player in enumerate(game.players):
        player.cards = list(hands[i])
        player.revealed = list(exposed[i])
        player.alive = bool(player.cards)
        player.coins = (coins[i] if coins is not None else (1 if n == 2 and i == 0 else 2)) if player.alive else 0
    game.deck = [role for role in ROLES for _ in range(3 - used[role])]
    game.rng.shuffle(game.deck)
    game.assert_valid_state()
    return game


def play(game, actor, action, target=None):
    """Choose a legal action while leaving challenge and block resolution live."""
    assert game.players[actor].alive
    assert action in ("income", "foreign_aid", "coup", *CLAIMS)
    coins = game.players[actor].coins
    assert coins < 10 or action == "coup"
    assert action != "coup" or coins >= 7
    assert action != "assassinate" or coins >= 3
    if action in ("coup", "assassinate", "steal"):
        assert target is not None and target != actor and game.players[target].alive
    else:
        assert target is None
    with ExitStack() as stack:
        stack.enter_context(patch.object(game, "_choose_action", return_value=action))
        if target is not None:
            stack.enter_context(patch.object(game, "_target", return_value=target))
        game.step(actor)
    game.assert_valid_state()


class SetupAndInformationTests(TestCase):
    def test_every_initial_player_count_conserves_cards_and_coins(self):
        for n in range(2, 7):
            with self.subTest(players=n):
                game = Game(n, seed=n)
                game.assert_valid_state()
                self.assertEqual(len(game.deck), 15 - 2 * n)
                self.assertEqual([p.influence() for p in game.players], [2] * n)
                self.assertEqual([p.coins for p in game.players], [1, 2] if n == 2 else [2] * n)

    def test_invalid_setup_rejected(self):
        for n in (0, 1, 7):
            with self.subTest(players=n), self.assertRaises(ValueError):
                Game(n)
        for bad in (0, -1):
            with self.subTest(turn_cap=bad), self.assertRaises(ValueError):
                Game(3, max_turns=bad)
        for bad in (("income",), ("income", "income", "unknown")):
            with self.subTest(policies=bad), self.assertRaises(ValueError):
                Game(3, policies=bad)

    def test_hidden_opponent_and_deck_cards_do_not_enter_observation(self):
        game = arranged(
            [("duke", "assassin"), ("captain", "ambassador"), ("contessa", "duke")]
        )
        before = game.observation(0)
        self.assertEqual(set(before), {"self_cards", "self_coins", "public"})
        self.assertEqual(before["self_cards"], ("duke", "assassin"))
        # Change another player's hidden card through a legal deck swap.
        deck_card = game.deck.index("assassin")
        game.players[1].cards[0], game.deck[deck_card] = game.deck[deck_card], game.players[1].cards[0]
        game.deck.reverse()
        game.assert_valid_state()
        self.assertEqual(game.observation(0), before)
        self.assertNotEqual(game.observation(1)["self_cards"], ("captain", "ambassador"))

    def test_lost_influence_becomes_public_and_cannot_be_used(self):
        game = arranged(
            [("duke", "assassin"), ("captain", "ambassador"), ("contessa", "duke")]
        )
        game._lose(1, forced="captain")
        game.assert_valid_state()
        for observer in (0, 1, 2):
            self.assertEqual(game.observation(observer)["public"][1][2], ("captain",))
            self.assertEqual(game.observation(observer)["public"][1][1], 1)
        self.assertEqual(game.observation(1)["self_cards"], ("ambassador",))
        self.assertNotIn("captain", game.players[1].cards)


class GeneralActionTests(TestCase):
    def test_income_cannot_be_challenged_or_blocked(self):
        game = arranged(
            [("duke", "assassin"), ("duke", "contessa"), ("captain", "ambassador")],
            policies=["income", "challenge_heavy", "challenge_heavy"],
        )
        play(game, 0, "income")
        self.assertEqual(game.players[0].coins, 3)
        self.assertEqual(game.events, [("action", 0, "income", None)])

    def test_unblocked_foreign_aid_cannot_be_challenged(self):
        game = arranged(
            [("duke", "assassin"), ("captain", "ambassador"), ("contessa", "assassin")],
            policies=["foreign_aid", "challenge_heavy", "challenge_heavy"],
        )
        play(game, 0, "foreign_aid")
        self.assertEqual(game.players[0].coins, 4)
        self.assertEqual(game.events, [("action", 0, "foreign_aid", None)])

    def test_duke_blocks_foreign_aid_and_proves_card_if_challenged(self):
        for challenge in (False, True):
            with self.subTest(challenge=challenge):
                game = arranged(
                    [("assassin", "captain"), ("duke", "contessa"), ("ambassador", "assassin")],
                    policies=["challenge_heavy" if challenge else "foreign_aid", "baseline", "baseline"],
                )
                play(game, 0, "foreign_aid")
                self.assertEqual(game.players[0].coins, 2)
                self.assertIn(("block", 1, "duke", "foreign_aid"), game.events)
                if challenge:
                    self.assertIn(("challenge", 0, 1, "duke"), game.events)
                    self.assertIn(("proved", 1, "duke"), game.events)
                    self.assertEqual(game.players[0].influence(), 1)
                    self.assertEqual(game.players[1].influence(), 2)
                else:
                    self.assertEqual([p.influence() for p in game.players], [2, 2, 2])

    def test_false_duke_block_challenged_by_actor_or_third_party(self):
        for challenger in (0, 2):
            with self.subTest(challenger=challenger):
                names = ["baseline", "block_aggressive", "baseline"]
                names[challenger] = "challenge_heavy"
                game = arranged(
                    [("assassin", "captain"), ("contessa", "ambassador"), ("duke", "assassin")],
                    policies=names,
                )
                play(game, 0, "foreign_aid")
                self.assertIn(("challenge", challenger, 1, "duke"), game.events)
                self.assertIn(("disproved", 1, "duke"), game.events)
                self.assertEqual(game.players[1].influence(), 1)
                self.assertEqual(game.players[0].coins, 4)

    def test_coup_costs_seven_and_ignores_challenges_and_blocks(self):
        game = arranged(
            [("assassin", "duke"), ("contessa", "captain"), ("ambassador", "duke")],
            coins=[7, 4, 2],
            policies=["income", "challenge_heavy", "challenge_heavy"],
        )
        play(game, 0, "coup", 1)
        self.assertEqual(game.players[0].coins, 0)
        self.assertEqual(game.players[1].influence(), 1)
        self.assertEqual(game.players[1].coins, 4)
        self.assertFalse(any(event[0] in ("challenge", "block") for event in game.events))

    def test_ten_coins_forces_coup_for_every_policy(self):
        for policy in POLICIES:
            with self.subTest(policy=policy):
                game = arranged(
                    [("assassin", "duke"), ("contessa",), ("captain", "ambassador")],
                    revealed=[(), ("duke",), ()],
                    coins=[10, 3, 2],
                    policies=[policy, "challenge_heavy", "challenge_heavy"],
                )
                game.failed_streak[0] = 5
                game.step(0)
                game.assert_valid_state()
                self.assertEqual(game.events[0], ("action", 0, "coup", 1))
                self.assertFalse(game.players[1].alive)
                self.assertEqual(game.players[1].coins, 0)
                self.assertEqual(game.players[0].coins, 3)


class CharacterActionTests(TestCase):
    def test_truthful_tax_survives_challenge_and_replaces_proved_card(self):
        game = arranged(
            [("duke", "assassin"), ("captain", "contessa"), ("ambassador", "duke")],
            policies=["baseline", "challenge_heavy", "baseline"],
        )
        court_before = len(game.deck)
        play(game, 0, "tax")
        self.assertEqual(game.players[0].coins, 5)
        self.assertEqual(game.players[0].influence(), 2)
        self.assertEqual(game.players[1].influence(), 1)
        self.assertEqual(len(game.deck), court_before)
        self.assertIn(("challenge", 1, 0, "duke"), game.events)
        self.assertIn(("proved", 0, "duke"), game.events)
        self.assertEqual(game.players[0].revealed, [])

    def test_false_tax_loses_influence_and_collects_nothing(self):
        game = arranged(
            [("captain", "assassin"), ("duke", "contessa"), ("ambassador", "duke")],
            policies=["taxer", "challenge_heavy", "baseline"],
        )
        before = len(game.deck)
        play(game, 0, "tax")
        self.assertEqual(game.players[0].coins, 2)
        self.assertEqual(game.players[0].influence(), 1)
        self.assertEqual(len(game.deck), before)
        self.assertIn(("disproved", 0, "duke"), game.events)
        self.assertNotIn(("proved", 0, "duke"), game.events)

    def test_assassination_spends_three_and_can_remove_last_influence(self):
        game = arranged(
            [("assassin", "duke"), ("captain",), ("ambassador", "duke")],
            revealed=[(), ("contessa",), ()],
            coins=[5, 4, 2],
            policies=["assassin", "baseline", "baseline"],
        )
        play(game, 0, "assassinate", 1)
        self.assertEqual(game.players[0].coins, 2)
        self.assertFalse(game.players[1].alive)
        self.assertEqual(game.players[1].coins, 0)
        self.assertEqual(game.players[1].influence(), 0)

    def test_false_assassin_challenge_refunds_fee_or_returns_coins_if_eliminated(self):
        for last_influence in (False, True):
            with self.subTest(last_influence=last_influence):
                hand = ("captain",) if last_influence else ("captain", "duke")
                exposed = ("ambassador",) if last_influence else ()
                game = arranged(
                    [hand, ("contessa", "duke"), ("assassin", "ambassador")],
                    revealed=[exposed, (), ()],
                    coins=[5, 2, 2],
                    policies=["assassin", "challenge_heavy", "baseline"],
                )
                play(game, 0, "assassinate", 1)
                self.assertEqual(game.players[1].influence(), 2)
                self.assertIn(("disproved", 0, "assassin"), game.events)
                self.assertFalse(any(event[0] == "block" for event in game.events))
                self.assertEqual(game.players[0].coins, 0 if last_influence else 5)
                self.assertEqual(game.players[0].influence(), 0 if last_influence else 1)

    def test_target_challenging_real_assassin_loses_two_influence(self):
        game = arranged(
            [("assassin", "duke"), ("captain", "ambassador"), ("contessa", "duke")],
            coins=[5, 4, 2],
            policies=["assassin", "challenge_heavy", "baseline"],
        )
        play(game, 0, "assassinate", 1)
        self.assertIn(("challenge", 1, 0, "assassin"), game.events)
        self.assertIn(("proved", 0, "assassin"), game.events)
        self.assertEqual(game.players[1].influence(), 0)
        self.assertFalse(game.players[1].alive)
        self.assertEqual(game.players[1].coins, 0)
        self.assertEqual(game.players[0].coins, 2)

    def test_truthful_contessa_block_keeps_assassin_fee_spent(self):
        game = arranged(
            [("assassin", "duke"), ("contessa", "captain"), ("ambassador", "duke")],
            coins=[5, 4, 2],
            policies=["challenge_heavy", "baseline", "baseline"],
        )
        play(game, 0, "assassinate", 1)
        self.assertIn(("challenge", 0, 1, "contessa"), game.events)
        self.assertIn(("proved", 1, "contessa"), game.events)
        self.assertEqual(game.players[1].influence(), 2)
        self.assertEqual(game.players[0].influence(), 1)
        self.assertEqual(game.players[0].coins, 2)

    def test_action_challenge_precedes_block_and_both_claims_can_be_challenged(self):
        game = arranged(
            [("assassin", "duke"), ("contessa", "captain"), ("ambassador", "duke")],
            coins=[5, 4, 2],
            policies=["assassin", "baseline", "challenge_heavy"],
        )
        play(game, 0, "assassinate", 1)
        action_challenge = game.events.index(("challenge", 2, 0, "assassin"))
        block = game.events.index(("block", 1, "contessa", "assassinate"))
        block_challenge = game.events.index(("challenge", 2, 1, "contessa"))
        self.assertLess(action_challenge, block)
        self.assertLess(block, block_challenge)
        self.assertFalse(game.players[2].alive)
        self.assertEqual(game.players[1].influence(), 2)
        self.assertEqual(game.players[0].coins, 2)

    def test_actor_eliminated_by_real_contessa_block_challenge(self):
        game = arranged(
            [("assassin",), ("contessa", "captain"), ("ambassador", "duke")],
            revealed=[("duke",), (), ()],
            coins=[5, 4, 2],
            policies=["challenge_heavy", "baseline", "baseline"],
        )
        play(game, 0, "assassinate", 1)
        self.assertFalse(game.players[0].alive)
        self.assertEqual(game.players[0].coins, 0)
        self.assertEqual(game.players[1].influence(), 2)
        self.assertIn(("proved", 1, "contessa"), game.events)

    def test_false_contessa_block_can_cost_target_two_influence(self):
        game = arranged(
            [("assassin", "duke"), ("captain", "ambassador"), ("contessa", "duke")],
            coins=[5, 4, 2],
            policies=["challenge_heavy", "block_aggressive", "baseline"],
        )
        play(game, 0, "assassinate", 1)
        self.assertIn(("disproved", 1, "contessa"), game.events)
        self.assertFalse(game.players[1].alive)
        self.assertEqual(game.players[1].influence(), 0)
        self.assertEqual(game.players[0].coins, 2)

    def test_steal_takes_two_or_one_coin_after_truthful_challenge(self):
        for target_coins in (1, 4):
            with self.subTest(target_coins=target_coins):
                game = arranged(
                    [("captain", "assassin"), ("duke", "contessa"), ("ambassador", "duke")],
                    coins=[2, target_coins, 2],
                    policies=["captain", "challenge_heavy", "baseline"],
                )
                play(game, 0, "steal", 1)
                amount = min(2, target_coins)
                self.assertIn(("proved", 0, "captain"), game.events)
                self.assertEqual(game.players[0].coins, 2 + amount)
                self.assertEqual(game.players[1].coins, target_coins - amount)
                self.assertEqual(game.players[1].influence(), 1)

    def test_steal_can_be_blocked_by_captain_or_ambassador(self):
        for block_role in ("captain", "ambassador"):
            for challenge in (False, True):
                with self.subTest(block_role=block_role, challenge=challenge):
                    game = arranged(
                        [("captain", "assassin"), (block_role, "contessa"), ("duke", "assassin")],
                        coins=[2, 4, 2],
                        policies=["challenge_heavy" if challenge else "captain", "baseline", "baseline"],
                    )
                    play(game, 0, "steal", 1)
                    self.assertIn(("block", 1, block_role, "steal"), game.events)
                    self.assertEqual((game.players[0].coins, game.players[1].coins), (2, 4))
                    self.assertEqual(game.players[1].influence(), 2)
                    if challenge:
                        self.assertIn(("challenge", 0, 1, block_role), game.events)
                        self.assertIn(("proved", 1, block_role), game.events)
                        self.assertEqual(game.players[0].influence(), 1)

    def test_false_steal_block_fails_and_steal_resolves(self):
        game = arranged(
            [("captain", "assassin"), ("duke", "contessa"), ("ambassador", "duke")],
            coins=[2, 4, 2],
            policies=["challenge_heavy", "block_aggressive", "baseline"],
        )
        play(game, 0, "steal", 1)
        self.assertIn(("disproved", 1, "captain"), game.events)
        self.assertEqual(game.players[1].influence(), 1)
        self.assertEqual((game.players[0].coins, game.players[1].coins), (4, 2))

    def test_eliminated_false_blocker_returns_coins_before_steal(self):
        game = arranged(
            [("captain", "assassin"), ("duke",), ("ambassador", "contessa")],
            revealed=[(), ("contessa",), ()],
            coins=[2, 4, 2],
            policies=["challenge_heavy", "block_aggressive", "baseline"],
        )
        play(game, 0, "steal", 1)
        self.assertFalse(game.players[1].alive)
        self.assertEqual(game.players[1].coins, 0)
        self.assertEqual(game.players[0].coins, 2)
        self.assertIn(("disproved", 1, "captain"), game.events)

    def test_challenged_true_exchange_resolves_after_card_replacement(self):
        game = arranged(
            [("ambassador", "contessa"), ("duke", "captain"), ("assassin", "duke")],
            policies=["exchange", "challenge_heavy", "baseline"],
        )
        court_before = len(game.deck)
        play(game, 0, "exchange")
        self.assertIn(("proved", 0, "ambassador"), game.events)
        self.assertIn(("exchange", 0), game.events)
        self.assertEqual(game.players[0].influence(), 2)
        self.assertEqual(game.players[1].influence(), 1)
        self.assertEqual(len(game.deck), court_before)

    def test_false_exchange_challenge_stops_before_drawing(self):
        game = arranged(
            [("duke", "captain"), ("assassin", "contessa"), ("ambassador", "duke")],
            policies=["bluff_heavy", "challenge_heavy", "baseline"],
        )
        court_before = tuple(game.deck)
        play(game, 0, "exchange")
        self.assertIn(("disproved", 0, "ambassador"), game.events)
        self.assertNotIn(("exchange", 0), game.events)
        self.assertEqual(tuple(game.deck), court_before)
        self.assertEqual(game.players[0].influence(), 1)

    def test_one_influence_exchange_with_duplicate_draw_does_not_restore_influence(self):
        game = arranged(
            [("captain",), ("duke", "assassin"), ("ambassador", "contessa")],
            revealed=[("contessa",), (), ()],
        )
        for _ in range(2):
            game.deck.remove("captain")
            game.deck.append("captain")
        court_before = len(game.deck)
        play(game, 0, "exchange")  # an unchallenged bluff is allowed
        self.assertEqual(game.players[0].cards, ["captain"])
        self.assertEqual(game.players[0].revealed, ["contessa"])
        self.assertEqual(game.players[0].influence(), 1)
        self.assertEqual(len(game.deck), court_before)

    def test_two_influence_exchange_conserves_identical_copies(self):
        game = arranged(
            [("captain", "ambassador"), ("duke", "assassin"), ("contessa", "duke")]
        )
        for _ in range(2):
            game.deck.remove("captain")
            game.deck.append("captain")
        play(game, 0, "exchange")
        self.assertEqual(game.players[0].cards, ["captain", "captain"])
        self.assertEqual(game.players[0].influence(), 2)
        self.assertEqual(Counter(game.deck)["captain"], 1)


class TurnAndIdentityTests(TestCase):
    def test_clockwise_challenger_and_blocker_conventions(self):
        game = arranged(
            [("captain", "assassin"), ("ambassador", "contessa"),
             ("duke", "assassin"), ("duke", "captain")],
            policies=["challenge_heavy", "baseline", "baseline", "challenge_heavy"],
        )
        play(game, 2, "tax")
        self.assertIn(("challenge", 3, 2, "duke"), game.events)
        self.assertEqual(game.players[3].influence(), 1)
        self.assertEqual(game.players[0].influence(), 2)

        blocked = arranged(
            [("assassin", "contessa"), ("duke", "captain"),
             ("duke", "ambassador"), ("assassin", "contessa")],
            policies=["foreign_aid", "baseline", "baseline", "baseline"],
        )
        play(blocked, 0, "foreign_aid")
        self.assertIn(("block", 1, "duke", "foreign_aid"), blocked.events)
        self.assertNotIn(("block", 2, "duke", "foreign_aid"), blocked.events)

    def test_eliminated_responder_is_skipped(self):
        game = arranged(
            [("duke", "assassin"), (), ("captain", "ambassador"), ("contessa", "duke")],
            revealed=[(), ("assassin", "contessa"), (), ()],
            policies=["baseline", "challenge_heavy", "challenge_heavy", "baseline"],
        )
        play(game, 0, "tax")
        self.assertIn(("challenge", 2, 0, "duke"), game.events)
        self.assertEqual(game.players[1].influence(), 0)
        self.assertEqual(game.players[1].coins, 0)

    def test_run_returns_surviving_seat_and_counts_live_actions(self):
        for survivor in (0, 1):
            with self.subTest(survivor=survivor):
                if survivor == 0:
                    game = arranged(
                        [("duke", "assassin"), ("captain",)],
                        revealed=[(), ("contessa",)],
                        coins=[7, 2], policies=["income", "challenge_heavy"],
                    )
                else:
                    game = arranged(
                        [("contessa",), ("captain", "assassin")],
                        revealed=[("duke",), ()],
                        coins=[1, 7], policies=["income", "income"],
                    )
                self.assertEqual(game.run(), survivor)
                self.assertEqual(game.alive(), [survivor])
                self.assertEqual(game.turn, 1 if survivor == 0 else 2)

        skipped = arranged(
            [("duke", "assassin"), (), ("captain", "ambassador")],
            revealed=[(), ("contessa", "duke"), ()],
            policies=["income", "challenge_heavy", "income"],
            max_turns=2,
        )
        self.assertIsNone(skipped.run())
        self.assertEqual(skipped.turn, 2)
        self.assertEqual([event[1] for event in skipped.events if event[0] == "action"], [0, 2])

    def test_experiment_win_rates_are_keyed_by_seat(self):
        names = ["income", "taxer", "captain"]
        seed, games = 714, 18
        manual = Counter(Game(3, seed + k, names).run() for k in range(games))
        rates, completed = experiment(games=games, players=3, seed=seed, policies=names)
        self.assertEqual(set(rates), {0, 1, 2})
        for seat in range(3):
            self.assertEqual(rates[seat], manual[seat] / games)
        self.assertEqual(completed, (games - manual[None]) / games)

    def test_seeded_games_preserve_rules_after_every_action(self):
        chooser = Random(8341)
        for n in range(2, 7):
            for case in range(24):
                with self.subTest(players=n, case=case):
                    names = [chooser.choice(POLICIES) for _ in range(n)]
                    game = Game(n, seed=100_000 * n + case, policies=names)
                    game.assert_valid_state()
                    seat = 0
                    while len(game.alive()) > 1 and game.turn < game.max_turns:
                        if game.players[seat].alive:
                            before_coins = game.players[seat].coins
                            living_before = set(game.alive())
                            event_start = len(game.events)
                            game.step(seat)
                            actions = [e for e in game.events[event_start:] if e[0] == "action"]
                            self.assertEqual(len(actions), 1)
                            _, actor, action, target = actions[0]
                            self.assertEqual(actor, seat)
                            self.assertIn(action, ("income", "foreign_aid", "coup", *CLAIMS))
                            if before_coins >= 10:
                                self.assertEqual(action, "coup")
                            if action == "coup":
                                self.assertGreaterEqual(before_coins, 7)
                            if action == "assassinate":
                                self.assertGreaterEqual(before_coins, 3)
                            if action in ("coup", "assassinate", "steal"):
                                self.assertIn(target, living_before - {actor})
                            else:
                                self.assertIsNone(target)
                            game.turn += 1
                            game.assert_valid_state()
                        seat = (seat + 1) % n
                    self.assertLessEqual(game.turn, game.max_turns)
                    if len(game.alive()) == 1:
                        self.assertIn(game.alive()[0], range(n))


if __name__ == "__main__":
    main()
