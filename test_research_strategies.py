"""Independent public-information and rule-contract tests for ResearchGame.

The large seeded check uses strict validation after every step. Small fixtures
account for all 15 cards and assert outcomes rather than just helper calls.
"""

from collections import Counter
from math import comb
from random import Random
from unittest import TestCase, main
from unittest.mock import patch

from coup_simulator import CLAIMS, POLICIES, ROLES, Game
import research_strategies as strategy_module
from research_strategies import (
    PRESETS,
    Config,
    ResearchGame,
    availability,
    challenge,
    claim_probability,
    no_opponent_role_probability,
)


def arranged(hands, *, revealed=None, coins=None, names=None, seed=412, strict=True):
    """Construct a reachable card inventory, including every face-up loss."""
    n = len(hands)
    exposed = revealed if revealed is not None else [()] * n
    if len(exposed) != n or any(len(hand) + len(face_up) != 2 for hand, face_up in zip(hands, exposed)):
        raise ValueError("each player must account for two physical cards")
    used = Counter(role for group in list(hands) + list(exposed) for role in group)
    if any(role not in ROLES for role in used) or any(used[role] > 3 for role in ROLES):
        raise ValueError("fixture exceeds the three copies of a role")
    game = ResearchGame(n, seed, names, strict=strict)
    for seat, player in enumerate(game.players):
        player.cards = list(hands[seat])
        player.revealed = list(exposed[seat])
        player.alive = bool(player.cards)
        player.coins = (coins[seat] if coins is not None else (1 if n == 2 and seat == 0 else 2)) if player.alive else 0
    game.deck = [role for role in ROLES for _ in range(3 - used[role])]
    game.rng.shuffle(game.deck)
    game.validate()
    return game


def scripted_step(game, actor, action, target=None, challenger=None, block=None):
    """Fix policy choices, then execute the real frozen action-resolution path."""
    assert game.players[actor].alive
    assert action in ("income", "foreign_aid", "coup", *CLAIMS)
    assert game.players[actor].coins < 10 or action == "coup"
    if action == "coup":
        assert game.players[actor].coins >= 7
    if action == "assassinate":
        assert game.players[actor].coins >= 3
    with patch.object(game, "_choose_action", return_value=action):
        with patch.object(game, "_target", return_value=target):
            with patch.object(game, "_challenger", return_value=challenger):
                if block is None:
                    game.step(actor)
                else:
                    with patch.object(game, "_block", return_value=block):
                        game.step(actor)
    game.validate()


class PriorAndChallengeTests(TestCase):
    def test_uniform_card_prior_exact_for_two_and_one_influence(self):
        game = arranged(
            [("duke", "contessa"), ("assassin", "captain"), ("ambassador", "duke")]
        )
        view = game.view(0)
        expected = 1 - comb(11, 2) / comb(13, 2)
        self.assertAlmostEqual(availability(view, 1, "duke"), expected)
        game._lose(1, forced="captain")
        game.validate()
        single = game.view(0)
        # One Duke in our hand leaves two among 12 unknown physical cards.
        self.assertAlmostEqual(availability(single, 1, "duke"), 2 / 12)

    def test_no_opponent_role_prior_uses_exact_joint_card_allocation(self):
        game = arranged(
            [("duke", "contessa"), ("assassin", "captain"), ("ambassador", "duke")]
        )
        # Nine Court cards among 13 unknown; two Duke copies remain unknown.
        self.assertAlmostEqual(
            no_opponent_role_probability(game.view(0), "duke"),
            comb(9, 2) / comb(13, 2),
        )
        game._lose(2, forced="duke")
        game.validate()
        # One Duke copy remains, with nine Court cards among 12 unknown.
        self.assertAlmostEqual(
            no_opponent_role_probability(game.view(0), "duke"),
            9 / 12,
        )

    def test_three_accounted_copies_make_role_impossible(self):
        game = arranged(
            [("duke", "duke"), ("assassin", "captain"), ("ambassador",)],
            revealed=[(), (), ("duke",)],
            names=["card_cautious", "card_balanced", "card_bold"],
        )
        view = game.view(0)
        self.assertEqual(availability(view, 1, "duke"), 0.0)
        self.assertEqual(claim_probability(view, 1, "duke", PRESETS["card_cautious"]), 0.0)
        self.assertTrue(challenge(view, 1, "duke", PRESETS["card_cautious"]))

    def test_claim_card_ablation_uses_a_non_card_prior(self):
        game = arranged(
            [("duke", "duke"), ("assassin", "captain"), ("ambassador",)],
            revealed=[(), (), ("duke",)],
        )
        view = game.view(0)
        self.assertIn("ablate_no_claim_cards", PRESETS)
        self.assertEqual(claim_probability(view, 1, "duke", PRESETS["public_learning"]), 0.0)
        self.assertGreater(claim_probability(view, 1, "duke", PRESETS["ablate_no_claim_cards"]), 0.0)

    def test_public_proof_without_face_up_loss_does_not_create_impossibility(self):
        game = arranged(
            [("duke", "contessa"), ("assassin", "captain"), ("ambassador", "duke")]
        )
        before = availability(game.view(0), 1, "duke")
        with patch.object(game, "_challenger", return_value=0):
            self.assertTrue(game._claim_stands(2, "duke"))
        game.validate()
        self.assertIn(("proved", 2, "duke"), game.view(0)["history"])
        self.assertEqual(availability(game.view(0), 1, "duke"), before)
        self.assertGreater(before, 0)

    def test_challenge_target_context_changes_decision(self):
        game = arranged(
            [("captain", "duke"), ("assassin", "ambassador"), ("contessa", "duke")],
            names=["card_cautious", "card_balanced", "card_balanced"],
        )
        # At this prior, losing one card versus risking two changes the wager.
        cfg = Config("target-context", assumed_bluff=0.8)
        two = game.view(0)
        two["history"] = (("action", 1, "assassinate", 0),)
        self.assertFalse(challenge(two, 1, "assassin", cfg))
        game._lose(0, forced="duke")
        game.validate()
        one = game.view(0)
        one["history"] = (("action", 1, "assassinate", 0),)
        self.assertTrue(challenge(one, 1, "assassin", cfg))
        one["history"] = (("action", 1, "assassinate", 2),)
        self.assertFalse(challenge(one, 1, "assassin", cfg))

    def test_blocked_own_action_has_distinct_challenge_value(self):
        game = arranged(
            [("assassin", "captain"), ("duke", "contessa"), ("ambassador", "assassin")]
        )
        cfg = Config("context", assumed_bluff=0.8)
        view = game.view(0)
        self.assertFalse(challenge(view, 1, "duke", cfg))
        view["history"] = (
            ("action", 0, "foreign_aid", None),
            ("block", 1, "duke", "foreign_aid"),
        )
        self.assertTrue(challenge(view, 1, "duke", cfg))
        view["history"] = (
            ("action", 2, "foreign_aid", None),
            ("block", 1, "duke", "foreign_aid"),
        )
        self.assertFalse(challenge(view, 1, "duke", cfg))


class InformationBoundaryTests(TestCase):
    def test_same_own_and_public_state_yields_same_choices_after_hidden_swap(self):
        names = ["public_learning", "card_bold", "baseline", "card_balanced"]
        hands = [
            ("captain", "contessa"), ("duke", "assassin"),
            ("ambassador", "captain"), ("duke", "contessa"),
        ]
        first = arranged(hands, names=names, seed=971)
        second = arranged(hands, names=names, seed=971)
        # Replace an opponent's concealed card with a Court card; visible data is identical.
        old = second.players[1].cards[0]
        deck_index = next(i for i, role in enumerate(second.deck) if role != old)
        second.players[1].cards[0], second.deck[deck_index] = second.deck[deck_index], old
        second.deck.reverse()
        second.validate()
        self.assertEqual(first.view(0), second.view(0))
        self.assertNotEqual(first.players[1].cards, second.players[1].cards)
        self.assertNotEqual(first.deck, second.deck)
        self.assertEqual(first._choose_action(0), second._choose_action(0))
        self.assertEqual(first._target(0, "steal"), second._target(0, "steal"))
        self.assertEqual(
            challenge(first.view(0), 1, "duke", PRESETS["public_learning"]),
            challenge(second.view(0), 1, "duke", PRESETS["public_learning"]),
        )
        self.assertEqual(first.decision_rng[0].getstate(), second.decision_rng[0].getstate())

    def test_opponent_strategy_labels_are_absent_from_public_view(self):
        one = ResearchGame(4, 710, ["public_learning", "card_bold", "baseline", "taxer"])
        two = ResearchGame(4, 710, ["public_learning", "defensive", "income", "captain"])
        self.assertEqual(one.view(0), two.view(0))
        self.assertEqual(one._choose_action(0), two._choose_action(0))

    def test_decisions_never_advance_environment_random_stream(self):
        for names in (
            ["public_learning", "card_bold", "card_balanced"],
            ["baseline", "bluff_heavy", "challenge_low"],
        ):
            with self.subTest(names=names):
                game = ResearchGame(3, 981, names, strict=True)
                environment_before = game.rng.getstate()
                game._choose_action(0)
                game._target(0, "steal")
                game._challenger(0, "duke")
                game._block(0, "foreign_aid")
                self.assertEqual(game.rng.getstate(), environment_before)
                game.validate()

    def test_only_public_events_reach_history_and_new_games_reset_it(self):
        names = ["public_learning", "baseline", "card_balanced"]
        game = arranged(
            [("duke", "assassin"), ("captain", "ambassador"), ("contessa", "duke")],
            names=names, seed=815,
        )
        initial = game.view(0)
        self.assertEqual(initial["history"], ())
        self.assertEqual(set(initial), {"self_cards", "self_coins", "public", "seat", "history", "failed_streak"})
        self.assertNotIn("names", initial)
        self.assertNotIn("deck", initial)
        self.assertNotIn("opponent_cards", initial)
        scripted_step(game, 0, "tax")
        game._lose(1, forced="captain")
        game.validate()
        history = game.view(0)["history"]
        self.assertEqual(history, tuple(game.events))
        self.assertIn(("lose", 1, "captain"), history)
        self.assertNotIn(("captain", "ambassador"), history)
        fresh = ResearchGame(3, 815, names, strict=True)
        self.assertEqual(fresh.view(0)["history"], ())
        self.assertEqual(fresh.action_counts, Counter())
        self.assertEqual(fresh.failed_streak, [0, 0, 0])


class AdapterRuleTests(TestCase):
    def test_public_random_can_choose_coup_or_another_action_at_seven_to_nine(self):
        for coins in (7, 8, 9):
            with self.subTest(coins=coins):
                seen = set()
                for seed in range(100):
                    game = ResearchGame(2, seed, ["public_random", "baseline"])
                    game.players[0].coins = coins
                    seen.add(game._choose_action(0))
                self.assertIn("coup", seen)
                self.assertGreater(len(seen - {"coup"}), 0)
        for seed in range(30):
            game = ResearchGame(2, seed, ["public_random", "baseline"])
            game.players[0].coins = 10
            self.assertEqual(game._choose_action(0), "coup")

    def test_random_target_is_sampled_once_after_action_selection(self):
        config = Config("target_once", bluff=0, exchange=0, target="random")
        with patch.dict(PRESETS, {"target_once": config}):
            game = arranged(
                [("captain", "ambassador"), ("duke",), ("contessa",)],
                revealed=[(), ("captain",), ("ambassador",)],
                coins=[2, 6, 6],
                names=["target_once", "baseline", "baseline"],
            )
            with patch("research_strategies.pick_target", wraps=strategy_module.pick_target) as picker:
                game.step(0)
            game.validate()
            self.assertEqual(game.events[0][2], "steal")
            self.assertEqual(picker.call_count, 1)
            self.assertIn(game.events[0][3], (1, 2))

    def test_legacy_and_new_policies_coexist_with_valid_card_state(self):
        game = ResearchGame(
            6, seed=2077,
            policies=["baseline", "public_learning", "bluff_heavy", "card_bold", "captain", "defensive"],
            strict=True,
        )
        winner = game.run()
        self.assertIsNotNone(winner)
        self.assertEqual(game.alive(), [winner])
        game.validate()
        self.assertEqual(sum(game.action_counts.values()), game.turn)

    def test_invalid_names_and_unaffordable_injected_actions_are_rejected(self):
        for names in (("card_balanced",), ("card_balanced", "missing")):
            with self.subTest(names=names), self.assertRaises(ValueError):
                ResearchGame(2, policies=names)
        game = ResearchGame(2, 108, ["card_balanced", "card_bold"], strict=True)
        with patch("research_strategies.choose_action", return_value="coup"):
            with self.assertRaisesRegex(ValueError, "Unaffordable action"):
                game._choose_action(0)
        with patch("research_strategies.choose_action", return_value="assassinate"):
            with self.assertRaisesRegex(ValueError, "Unaffordable action"):
                game._choose_action(0)

    def test_adapter_keeps_action_challenge_and_fee_rules(self):
        false_claim = arranged(
            [("captain", "duke"), ("contessa", "ambassador"), ("assassin", "duke")],
            coins=[5, 2, 2], names=["card_bold", "card_balanced", "baseline"],
        )
        scripted_step(false_claim, 0, "assassinate", target=1, challenger=1)
        self.assertEqual(false_claim.players[0].coins, 5)
        self.assertEqual(false_claim.players[0].influence(), 1)
        self.assertEqual(false_claim.players[1].influence(), 2)
        self.assertIn(("disproved", 0, "assassin"), false_claim.events)

        blocked = arranged(
            [("assassin", "duke"), ("contessa", "captain"), ("ambassador", "duke")],
            coins=[5, 2, 2], names=["public_learning", "defensive", "baseline"],
        )
        scripted_step(blocked, 0, "assassinate", target=1, challenger=None)
        self.assertEqual(blocked.players[0].coins, 2)
        self.assertEqual(blocked.players[1].influence(), 2)
        self.assertIn(("block", 1, "contessa", "assassinate"), blocked.events)

    def test_adapter_keeps_double_loss_and_mandatory_coup(self):
        double_loss = arranged(
            [("assassin", "duke"), ("captain", "ambassador"), ("contessa", "duke")],
            coins=[5, 4, 2], names=["public_learning", "card_bold", "baseline"],
        )
        scripted_step(double_loss, 0, "assassinate", target=1, challenger=1)
        self.assertFalse(double_loss.players[1].alive)
        self.assertEqual(double_loss.players[1].coins, 0)
        self.assertEqual(double_loss.players[0].coins, 2)
        self.assertIn(("proved", 0, "assassin"), double_loss.events)

        coup = arranged(
            [("assassin", "duke"), ("captain",), ("ambassador", "contessa")],
            revealed=[(), ("duke",), ()],
            coins=[10, 4, 2], names=["public_random", "card_bold", "baseline"],
        )
        coup.step(0)
        coup.validate()
        self.assertEqual(coup.events[0], ("action", 0, "coup", 1))
        self.assertEqual(coup.players[0].coins, 3)
        self.assertFalse(coup.players[1].alive)
        self.assertFalse(any(event[0] in ("challenge", "block") for event in coup.events))

    def test_one_influence_exchange_with_duplicate_cards_conserves_every_copy(self):
        game = arranged(
            [("captain",), ("duke", "assassin"), ("ambassador", "contessa")],
            revealed=[("contessa",), (), ()],
            names=["exchange_builder", "baseline", "card_bold"],
        )
        for _ in range(2):
            game.deck.remove("captain")
            game.deck.append("captain")
        court_before = len(game.deck)
        scripted_step(game, 0, "exchange")
        self.assertEqual(game.players[0].cards, ["captain"])
        self.assertEqual(game.players[0].revealed, ["contessa"])
        self.assertEqual(game.players[0].influence(), 1)
        self.assertEqual(len(game.deck), court_before)
        self.assertEqual(Counter(game.deck)["captain"], 2)

    def test_state_sensitive_influence_retention_and_fixed_ablation(self):
        hands = [("assassin", "contessa"), ("duke", "captain"), ("ambassador", "duke")]
        dynamic = arranged(hands, coins=[3, 7, 5], names=["defensive", "baseline", "baseline"])
        fixed = arranged(hands, coins=[3, 7, 5], names=["ablate_fixed_retention", "baseline", "baseline"])
        dynamic._lose(0)
        fixed._lose(0)
        dynamic.validate()
        fixed.validate()
        self.assertEqual(dynamic.players[0].cards, ["contessa"])
        self.assertEqual(dynamic.players[0].revealed, ["assassin"])
        self.assertEqual(fixed.players[0].cards, ["assassin"])
        self.assertEqual(fixed.players[0].revealed, ["contessa"])

    def test_exchange_retention_uses_drawn_cards_without_restoring_influence(self):
        game = arranged(
            [("ambassador",), ("captain", "assassin"), ("contessa", "duke")],
            revealed=[("contessa",), (), ()],
            coins=[2, 6, 2], names=["exchange_builder", "baseline", "baseline"],
        )
        for role in ("duke", "captain"):
            game.deck.remove(role)
            game.deck.append(role)
        scripted_step(game, 0, "exchange")
        self.assertEqual(game.players[0].cards, ["duke"])
        self.assertEqual(game.players[0].influence(), 1)
        self.assertEqual(game.players[0].revealed, ["contessa"])

    def test_ten_thousand_seeded_games_validate_every_step(self):
        # Strict mode calls validate() after each live action, including challenges.
        # Rotating the full policy list tests all new presets and legacy controls.
        names = list(PRESETS) + list(POLICIES)
        chooser = Random(104271)
        draws = 0
        covered = set()
        for case in range(10_000):
            n = 2 + case % 5
            lineup = [names[(case + j + chooser.randrange(len(names))) % len(names)] for j in range(n)]
            covered.update(lineup)
            game = ResearchGame(n, 40_000_000 + case, lineup, max_turns=1000, strict=True)
            winner = game.run()
            game.validate()
            self.assertEqual(sum(game.action_counts.values()), game.turn)
            self.assertTrue(set(game.action_counts) <= {"income", "foreign_aid", "tax", "steal", "assassinate", "exchange", "coup"})
            self.assertLessEqual(game.turn, game.max_turns)
            if winner is None:
                draws += 1
                self.assertGreater(len(game.alive()), 1)
            else:
                self.assertEqual(game.alive(), [winner])
        self.assertLess(draws, 10_000)
        self.assertEqual(covered, set(names))


if __name__ == "__main__":
    main()
