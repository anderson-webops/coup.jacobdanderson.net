"""Independent rule outcomes for Reformation and the Inquisitor variant.

Fixtures reconstruct the entire physical deck. Tests choose actions and
decisions, then check published outcomes rather than reproducing resolution.
"""

from collections import Counter
from dataclasses import FrozenInstanceError
from random import Random
from unittest import TestCase, main
from unittest.mock import patch

from expansion_simulator import Action, ExpansionGame


PROFILES = ("reformation", "inquisitor", "combined")


def arranged(hands, *, exposed=None, coins=None, allegiances=None, treasury=0,
             profile="combined", seed=17, identities=None):
    """Make a possible state; hidden and exposed cards always total two."""
    n = len(hands)
    game = ExpansionGame(n, seed, ["balanced"] * n, profile=profile,
                         strict=True, record=True, identities=identities)
    exposed = list(exposed) if exposed is not None else [()] * n
    if len(exposed) != n or any(len(h) + len(e) != 2 for h, e in zip(hands, exposed)):
        raise ValueError("fixture must account for two cards per player")
    used = Counter(card for group in list(hands) + exposed for card in group)
    if set(used) - set(game.roles) or any(used[r] > game.copies for r in game.roles):
        raise ValueError("fixture must fit the selected physical deck")
    for i, player in enumerate(game.players):
        player.cards = list(hands[i])
        player.exposed = list(exposed[i])
        player.coins = (coins[i] if coins is not None else 2) if player.cards else 0
        player.allegiance = allegiances[i] if allegiances is not None else i % 2
    game.deck = [role for role in game.roles for _ in range(game.copies - used[role])]
    Random(seed + 91).shuffle(game.deck)
    game.treasury = treasury
    game.bank_net = sum(p.coins for p in game.players) + treasury
    game.check_invariants()
    return game


def play(game, actor, kind, target=None, *, challenger=None, block=None):
    with patch.object(game, "_challenger", return_value=challenger), \
            patch.object(game, "_block", return_value=block):
        game.step(actor, Action(kind, target))
    game.check_invariants()


def normal_hands():
    return [("duke", "assassin"), ("captain", "contessa"),
            ("inquisitor", "duke"), ("assassin", "captain")]


class SetupAndObservationTests(TestCase):
    def test_all_profiles_and_two_through_ten_player_decks(self):
        for profile in PROFILES:
            for n in range(2, 11):
                with self.subTest(profile=profile, players=n):
                    game = ExpansionGame(n, 400 + n, ["balanced"] * n, profile=profile)
                    copies = 3 if n <= 6 else 4 if n <= 8 else 5
                    self.assertEqual(game.copies, copies)
                    self.assertEqual(len(game.roles), 5)
                    self.assertEqual(len(game.deck), 5 * copies - 2 * n)
                    self.assertEqual([len(p.cards) for p in game.players], [2] * n)
                    self.assertEqual([p.coins for p in game.players], [1, 2] if n == 2 else [2] * n)
                    self.assertEqual(game.treasury, 0)
                    self.assertEqual(Counter(game.deck + [c for p in game.players for c in p.cards]),
                                     Counter({r: copies for r in game.roles}))
                    if profile != "inquisitor":
                        self.assertEqual([p.allegiance for p in game.players], [i % 2 for i in range(n)])
                    self.assertEqual("inquisitor" in game.roles, profile != "reformation")
                    self.assertEqual("ambassador" in game.roles, profile == "reformation")
                    game.check_invariants()

    def test_invalid_player_counts_profiles_and_policy_lengths_rejected(self):
        for n in (0, 1, 11):
            with self.subTest(players=n), self.assertRaises(ValueError):
                ExpansionGame(n, 3, ["balanced"] * max(0, n))
        with self.assertRaises(ValueError):
            ExpansionGame(3, 3, ["balanced"] * 3, profile="unknown")
        with self.assertRaises(ValueError):
            ExpansionGame(3, 3, ["balanced"] * 2)
        with self.assertRaises(ValueError):
            ExpansionGame(3, 3, ["balanced"] * 3, max_turns=0)

    def test_identity_count_and_uniqueness_checked(self):
        for identities in ((0, 1), (0, 1, 1)):
            with self.subTest(identities=identities), self.assertRaises(ValueError):
                ExpansionGame(3, 3, ["balanced"] * 3, identities=identities)

    def test_action_is_immutable(self):
        action = Action("coup", 2)
        with self.assertRaises(FrozenInstanceError):
            action.target = 1

    def test_observation_contains_only_own_cards_and_public_fields(self):
        game = arranged(normal_hands())
        view = game.observation(0)
        self.assertEqual(view["own_cards"], ("duke", "assassin"))
        self.assertEqual(view["players"], tuple((2, 2, i % 2, ()) for i in range(4)))
        self.assertEqual(view["inspected"], ())
        self.assertEqual(view["self"], 0)
        for forbidden in ("deck", "opponent_cards", "rng", "seed", "policies"):
            self.assertNotIn(forbidden, view)

    def test_changing_unknown_hand_and_deck_order_does_not_change_observation(self):
        game = arranged(normal_hands())
        before = game.observation(0)
        game.players[1].cards[0], game.deck[0] = game.deck[0], game.players[1].cards[0]
        game.deck.reverse()
        game.check_invariants()
        self.assertEqual(game.observation(0), before)

    def test_exposed_cards_and_remaining_influence_are_public(self):
        game = arranged(normal_hands())
        with patch("expansion_policies.discard_index", return_value=0):
            game._lose(1)
        for i in range(4):
            self.assertEqual(game.observation(i)["players"][1], (2, 1, 1, ("captain",)))
        game.check_invariants()


class AllegianceAndGeneralActionTests(TestCase):
    def test_attacks_and_examine_cannot_target_allies(self):
        game = arranged(normal_hands(), coins=[8, 2, 2, 2])
        for kind in ("coup", "assassinate", "steal", "examine"):
            with self.subTest(kind=kind):
                self.assertFalse(game.eligible_target(0, 0, kind))
                self.assertFalse(game.eligible_target(0, 2, kind))
                self.assertTrue(game.eligible_target(0, 1, kind))
                self.assertNotIn(Action(kind, 2), game.available_actions(0))

    def test_everyone_same_allegiance_allows_attacks_and_examine(self):
        game = arranged(normal_hands(), coins=[8, 2, 2, 2], allegiances=[0] * 4)
        for kind in ("coup", "assassinate", "steal", "examine"):
            with self.subTest(kind=kind):
                self.assertTrue(game.eligible_target(0, 2, kind))
                self.assertIn(Action(kind, 2), game.available_actions(0))

    def test_inquisitor_without_allegiances_can_examine_any_opponent(self):
        game = arranged(normal_hands(), profile="inquisitor")
        self.assertTrue(game.eligible_target(0, 2, "examine"))
        self.assertIn(Action("examine", 2), game.available_actions(0))

    def test_conversion_reinstates_restrictions_after_single_faction(self):
        game = arranged(normal_hands(), allegiances=[0] * 4)
        play(game, 0, "convert_other", 1)
        self.assertEqual(game.players[1].allegiance, 1)
        self.assertFalse(game.eligible_target(0, 2, "examine"))
        self.assertTrue(game.eligible_target(0, 1, "examine"))

    def test_eliminating_last_other_faction_enables_remaining_allies(self):
        game = arranged([("duke", "assassin"), ("captain",), ("inquisitor", "duke")],
                        exposed=[(), ("contessa",), ()])
        self.assertFalse(game.eligible_target(0, 2, "examine"))
        game._lose(1)
        self.assertTrue(game.eligible_target(0, 2, "examine"))
        self.assertEqual(game.players[1].coins, 0)
        self.assertFalse(game.eligible_target(0, 1, "examine"))
        game.check_invariants()

    def test_self_conversion_costs_one_into_reserve(self):
        game = arranged(normal_hands(), treasury=3)
        initial_bank = game.bank_net
        play(game, 0, "convert_self")
        self.assertEqual((game.players[0].coins, game.players[0].allegiance, game.treasury), (1, 1, 4))
        self.assertEqual(game.bank_net, initial_bank)

    def test_other_conversion_costs_two_for_allies_or_enemies(self):
        for target in (1, 2):
            with self.subTest(target=target):
                game = arranged(normal_hands(), treasury=1)
                old = game.players[target].allegiance
                play(game, 0, "convert_other", target)
                self.assertEqual(game.players[target].allegiance, 1 - old)
                self.assertEqual(game.players[0].coins, 0)
                self.assertEqual(game.treasury, 3)

    def test_conversion_actions_unaffordable_at_zero_and_one(self):
        for coins in (0, 1, 2):
            with self.subTest(coins=coins):
                game = arranged(normal_hands(), coins=[coins, 2, 2, 2])
                actions = game.available_actions(0)
                self.assertEqual(Action("convert_self") in actions, coins >= 1)
                self.assertEqual(Action("convert_other", 1) in actions, coins >= 2)

    def test_ten_coins_only_allows_coups_on_legal_opponents(self):
        for profile in PROFILES:
            with self.subTest(profile=profile):
                role = "ambassador" if profile == "reformation" else "inquisitor"
                hands = [("duke", "assassin"), ("captain", "contessa"),
                         (role, "duke"), ("assassin", "captain")]
                game = arranged(hands, coins=[10, 2, 2, 2], profile=profile)
                actions = game.available_actions(0)
                self.assertTrue(actions)
                self.assertTrue(all(a.kind == "coup" for a in actions))
                self.assertEqual({a.target for a in actions}, {1, 2, 3} if profile == "inquisitor" else {1, 3})
                for forbidden in ("income", "embezzle", "convert_self", "tax", "exchange"):
                    with self.assertRaises(ValueError):
                        game.step(0, Action(forbidden))

    def test_expansion_actions_absent_without_corresponding_variant(self):
        game = ExpansionGame(4, 1, ["balanced"] * 4, profile="inquisitor")
        self.assertFalse({a.kind for a in game.available_actions(0)} &
                         {"convert_self", "convert_other", "embezzle"})
        game = ExpansionGame(4, 1, ["balanced"] * 4, profile="reformation")
        self.assertNotIn("examine", {a.kind for a in game.available_actions(0)})

    def test_income_is_unconditional_and_bank_supplies_one(self):
        game = arranged(normal_hands())
        initial_bank = game.bank_net
        with patch.object(game, "_challenger", side_effect=AssertionError("income challenged")), \
                patch.object(game, "_block", side_effect=AssertionError("income blocked")):
            game.step(0, Action("income"))
        self.assertEqual(game.players[0].coins, 3)
        self.assertEqual(game.bank_net, initial_bank + 1)
        game.check_invariants()

    def test_allied_duke_cannot_block_foreign_aid(self):
        game = arranged(normal_hands())
        def block_for_ally(view, *args, **kwargs):
            return "duke" if view["self"] == 2 else None
        with patch.object(game, "_challenger", return_value=None), \
                patch("expansion_policies.choose_block", side_effect=block_for_ally):
            game.step(0, Action("foreign_aid"))
        self.assertEqual(game.players[0].coins, 4)
        game.check_invariants()

    def test_opposing_duke_can_block_foreign_aid(self):
        game = arranged(normal_hands())
        def block_for_enemy(view, *args, **kwargs):
            return "duke" if view["self"] == 1 else None
        with patch.object(game, "_challenger", return_value=None), \
                patch("expansion_policies.choose_block", side_effect=block_for_enemy):
            game.step(0, Action("foreign_aid"))
        self.assertEqual(game.players[0].coins, 2)
        game.check_invariants()

    def test_same_faction_duke_blocks_when_everyone_shares_allegiance(self):
        game = arranged(normal_hands(), allegiances=[0] * 4)
        def block_for_ally(view, *args, **kwargs):
            return "duke" if view["self"] == 2 else None
        with patch.object(game, "_challenger", return_value=None), \
                patch("expansion_policies.choose_block", side_effect=block_for_ally):
            game.step(0, Action("foreign_aid"))
        self.assertEqual(game.players[0].coins, 2)
        game.check_invariants()

    def test_coup_spends_seven_and_elimination_returns_remaining_coins(self):
        game = arranged([("duke", "assassin"), ("captain",), ("inquisitor", "duke")],
                        exposed=[(), ("contessa",), ()], coins=[7, 5, 2])
        initial_bank = game.bank_net
        play(game, 0, "coup", 1)
        self.assertEqual(game.players[0].coins, 0)
        self.assertEqual(game.players[1].coins, 0)
        self.assertFalse(game.players[1].alive)
        self.assertEqual(game.bank_net, initial_bank - 12)

    def test_illegal_actions_rejected_without_changing_state(self):
        for action in (Action("unknown"), Action("coup", 1), Action("convert_other", 0),
                       Action("examine", 2), Action("steal", 99), Action("income", 1)):
            with self.subTest(action=action):
                game = arranged(normal_hands())
                before = (game.observation(0), tuple(game.deck), game.bank_net)
                with self.assertRaises(ValueError):
                    game.step(0, action)
                self.assertEqual((game.observation(0), tuple(game.deck), game.bank_net), before)


class ClaimAndEmbezzlementTests(TestCase):
    def test_truthful_claim_replaces_one_card_and_challenger_loses(self):
        game = arranged(normal_hands())
        self.assertTrue(game.resolve_claim(0, "duke", 1))
        self.assertEqual([len(p.cards) for p in game.players], [2, 1, 2, 2])
        game.check_invariants()

    def test_allies_may_challenge_character_claims(self):
        game = arranged(normal_hands())
        self.assertTrue(game.resolve_claim(0, "duke", 2))
        self.assertEqual(len(game.players[2].cards), 1)
        game.check_invariants()

    def test_false_claim_loses_only_claimant_influence(self):
        game = arranged(normal_hands())
        self.assertFalse(game.resolve_claim(0, "inquisitor", 1))
        self.assertEqual([len(p.cards) for p in game.players], [1, 2, 2, 2])
        game.check_invariants()

    def test_truthful_positive_claim_can_concede(self):
        game = arranged(normal_hands())
        before_deck = tuple(game.deck)
        self.assertFalse(game.resolve_claim(0, "duke", 1, concede=True))
        self.assertEqual(tuple(game.deck), before_deck)
        self.assertEqual(len(game.players[0].cards), 1)
        game.check_invariants()

    def test_negative_claim_with_duke_fails_even_with_another_nonduke(self):
        for hand in (("duke", "assassin"), ("duke", "duke")):
            with self.subTest(hand=hand):
                hands = normal_hands()
                hands[0] = hand
                if hand[1] == "duke":
                    hands[2] = ("inquisitor", "contessa")
                game = arranged(hands)
                self.assertFalse(game.resolve_claim(0, "duke", 1, negative=True))
                self.assertEqual([len(p.cards) for p in game.players], [1, 2, 2, 2])
                game.check_invariants()

    def test_truthful_negative_claim_replaces_whole_hand(self):
        game = arranged([("captain", "assassin"), ("duke", "contessa"),
                         ("inquisitor", "duke"), ("assassin", "captain")])
        seen = []
        def loss_index(view, *args, **kwargs):
            seen.append(view)
            return 0
        with patch("expansion_policies.discard_index", side_effect=loss_index):
            self.assertTrue(game.resolve_claim(0, "duke", 1, negative=True))
        self.assertEqual(len(game.players[0].cards), 2)
        self.assertEqual(len(game.players[1].cards), 1)
        self.assertTrue(seen)
        self.assertEqual(seen[0]["public_proof"], ((0, ("captain", "assassin")),))
        self.assertEqual(game.observation(1)["public_proof"], ())
        game.check_invariants()

    def test_truthful_negative_claim_with_one_card_preserves_one(self):
        game = arranged([("captain",), ("duke", "contessa"), ("inquisitor", "duke")],
                        exposed=[("assassin",), (), ()])
        self.assertTrue(game.resolve_claim(0, "duke", 1, negative=True))
        self.assertEqual(len(game.players[0].cards), 1)
        game.check_invariants()

    def test_exposed_duke_does_not_prevent_truthful_embezzlement(self):
        game = arranged([("captain",), ("duke", "contessa"), ("inquisitor", "assassin")],
                        exposed=[("duke",), (), ()], treasury=3)
        play(game, 0, "embezzle", challenger=1)
        self.assertEqual(game.players[0].coins, 5)
        self.assertEqual(game.treasury, 0)
        self.assertEqual(len(game.players[0].cards), 1)
        self.assertEqual(len(game.players[1].cards), 1)

    def test_duke_drawn_after_truthful_embezzlement_does_not_reverse_success(self):
        game = arranged([("captain", "assassin"), ("duke", "contessa"),
                         ("inquisitor", "duke"), ("assassin", "captain")], treasury=4)
        def put_dukes_on_top(deck):
            deck.sort(key=lambda role: role == "duke")
        with patch.object(game.rng, "shuffle", side_effect=put_dukes_on_top):
            play(game, 0, "embezzle", challenger=1)
        self.assertIn("duke", game.players[0].cards)
        self.assertEqual(game.players[0].coins, 6)
        self.assertEqual(game.treasury, 0)
        self.assertEqual(len(game.players[1].cards), 1)

    def test_truthful_negative_claim_may_concede_without_showing_hand(self):
        game = arranged([("captain", "assassin"), ("duke", "contessa"),
                         ("inquisitor", "duke"), ("assassin", "captain")])
        before_deck = tuple(game.deck)
        self.assertFalse(game.resolve_claim(0, "duke", 1, negative=True, concede=True))
        self.assertEqual(tuple(game.deck), before_deck)
        self.assertEqual(len(game.players[0].cards), 1)
        game.check_invariants()

    def test_unchallenged_embezzlement_collects_entire_reserve(self):
        game = arranged(normal_hands(), treasury=6)
        initial_bank = game.bank_net
        play(game, 0, "embezzle")
        self.assertEqual((game.players[0].coins, game.treasury), (8, 0))
        self.assertEqual(game.bank_net, initial_bank)

    def test_empty_reserve_embezzlement_remains_legal(self):
        game = arranged(normal_hands())
        self.assertIn(Action("embezzle"), game.available_actions(0))
        before = game.bank_net
        play(game, 0, "embezzle")
        self.assertEqual(game.players[0].coins, 2)
        self.assertEqual(game.treasury, 0)
        self.assertEqual(game.bank_net, before)

    def test_false_embezzlement_restores_reserve_before_elimination(self):
        game = arranged([("duke",), ("captain", "contessa"), ("inquisitor", "duke")],
                        exposed=[("assassin",), (), ()], coins=[4, 2, 2], treasury=7)
        initial_bank = game.bank_net
        play(game, 0, "embezzle", challenger=1)
        self.assertFalse(game.players[0].alive)
        self.assertEqual(game.players[0].coins, 0)
        self.assertEqual(game.treasury, 7)
        self.assertEqual(game.bank_net, initial_bank - 4)

    def test_truthful_embezzlement_keeps_money_after_replacement(self):
        game = arranged([("captain", "assassin"), ("duke", "contessa"),
                         ("inquisitor", "duke"), ("assassin", "captain")], treasury=5)
        play(game, 0, "embezzle", challenger=1)
        self.assertEqual((game.players[0].coins, game.treasury), (7, 0))
        self.assertEqual(len(game.players[0].cards), 2)
        self.assertEqual(len(game.players[1].cards), 1)

    def test_failed_assassin_claim_refunds_three(self):
        game = arranged([("captain", "duke"), ("assassin", "contessa"),
                         ("inquisitor", "duke"), ("assassin", "captain")], coins=[3, 2, 2, 2])
        play(game, 0, "assassinate", 1, challenger=2)
        self.assertEqual(game.players[0].coins, 3)
        self.assertEqual(len(game.players[0].cards), 1)
        self.assertEqual(len(game.players[1].cards), 2)

    def test_contessa_block_keeps_assassin_fee_spent(self):
        game = arranged(normal_hands(), coins=[3, 2, 2, 2])
        play(game, 0, "assassinate", 1, block=(1, "contessa"))
        self.assertEqual(game.players[0].coins, 0)
        self.assertEqual(len(game.players[1].cards), 2)

    def test_false_contessa_block_costs_one_then_assassination_costs_one(self):
        game = arranged(normal_hands(), coins=[3, 2, 2, 2])
        # Remove Contessa from the target's hidden hand through a physical swap.
        index = game.deck.index("inquisitor")
        game.players[1].cards[1], game.deck[index] = game.deck[index], game.players[1].cards[1]
        def challenger(claimant, role, negative=False):
            return 2 if claimant == 1 else None
        with patch.object(game, "_challenger", side_effect=challenger), \
                patch.object(game, "_block", return_value=(1, "contessa")):
            game.step(0, Action("assassinate", 1))
        self.assertFalse(game.players[1].alive)
        self.assertEqual(game.players[1].coins, 0)
        self.assertEqual(game.players[0].coins, 0)
        game.check_invariants()

    def test_false_steal_block_elimination_leaves_no_coins_to_steal(self):
        game = arranged([("captain", "duke"), ("assassin",), ("inquisitor", "duke")],
                        exposed=[(), ("contessa",), ()], coins=[2, 5, 2])
        # Only the block claim receives a challenge; the Captain claim succeeds.
        def challenger(claimant, role, negative=False):
            return 0 if claimant == 1 else None
        with patch.object(game, "_challenger", side_effect=challenger), \
                patch.object(game, "_block", return_value=(1, "inquisitor")):
            game.step(0, Action("steal", 1))
        self.assertFalse(game.players[1].alive)
        self.assertEqual(game.players[0].coins, 2)
        self.assertEqual(game.players[1].coins, 0)
        game.check_invariants()


class CardIntegrityTests(TestCase):
    def test_card_duplicate_and_coin_tampering_are_detected(self):
        for change in ("card", "coins", "treasury"):
            with self.subTest(change=change):
                game = arranged(normal_hands())
                if change == "card":
                    game.deck.append("duke")
                elif change == "coins":
                    game.players[0].coins += 1
                else:
                    game.treasury += 1
                with self.assertRaises((AssertionError, ValueError)):
                    game.check_invariants()

    def test_negative_coin_balance_is_detected_even_if_bookkeeping_balanced(self):
        game = arranged(normal_hands())
        game.players[0].coins = -1
        game.bank_net = sum(p.coins for p in game.players) + game.treasury
        with self.assertRaises((AssertionError, ValueError)):
            game.check_invariants()


class InquisitorAndReplacementTests(TestCase):
    def test_inquisitor_exchange_can_keep_duplicate_original_cards(self):
        game = arranged([("duke", "duke"), ("captain", "contessa"),
                         ("inquisitor", "assassin"), ("assassin", "captain")])
        before_deck_size = len(game.deck)
        with patch("expansion_policies.keep_indices", return_value=[0, 1]):
            game._exchange(0, 1)
        self.assertEqual(game.players[0].cards, ["duke", "duke"])
        self.assertEqual(len(game.deck), before_deck_size)
        game.check_invariants()

    def test_ambassador_exchange_keeps_two_duplicates_without_card_loss(self):
        game = arranged([("duke", "duke"), ("captain", "contessa"),
                         ("ambassador", "assassin"), ("assassin", "captain")],
                        profile="reformation")
        before_deck_size = len(game.deck)
        with patch("expansion_policies.keep_indices", return_value=[0, 1]):
            game._exchange(0, 2)
        self.assertEqual(game.players[0].cards, ["duke", "duke"])
        self.assertEqual(len(game.deck), before_deck_size)
        game.check_invariants()

    def test_exchange_with_one_influence_keeps_exactly_one(self):
        for profile, draw_count in (("reformation", 2), ("combined", 1)):
            with self.subTest(profile=profile):
                role = "ambassador" if profile == "reformation" else "inquisitor"
                game = arranged([(role,), ("captain", "contessa"), ("duke", "assassin")],
                                exposed=[("duke",), (), ()], profile=profile)
                before_deck_size = len(game.deck)
                with patch("expansion_policies.keep_indices", return_value=[0]):
                    game._exchange(0, draw_count)
                self.assertEqual(game.players[0].cards, [role])
                self.assertEqual(len(game.deck), before_deck_size)
                game.check_invariants()

    def test_examine_target_selects_card_and_only_inspector_learns_it(self):
        game = arranged(normal_hands())
        before_cards = list(game.players[1].cards)
        with patch("expansion_policies.show_index", return_value=1), \
                patch("expansion_policies.force_replace", return_value=False):
            game._examine(0, 1)
        self.assertEqual(game.players[1].cards, before_cards)
        self.assertEqual(game.observation(0)["inspected"], ((1, "contessa"),))
        self.assertEqual(game.observation(2)["inspected"], ())
        self.assertEqual(game.observation(3)["inspected"], ())
        self.assertNotIn("contessa", repr(game.events))
        game.check_invariants()

    def test_successful_challenge_stops_examine_before_any_private_view(self):
        game = arranged(normal_hands())
        before_target = list(game.players[1].cards)
        with patch("expansion_policies.show_index") as show, \
                patch("expansion_policies.force_replace") as force:
            play(game, 0, "examine", 1, challenger=2)
        show.assert_not_called()
        force.assert_not_called()
        self.assertEqual(game.players[1].cards, before_target)
        self.assertEqual(game.observation(0)["inspected"], ())
        self.assertEqual(len(game.players[0].cards), 1)

    def test_failed_allied_challenge_precedes_examine(self):
        game = arranged([("inquisitor", "duke"), ("captain", "contessa"),
                         ("assassin", "duke"), ("assassin", "captain")])
        with patch("expansion_policies.show_index", return_value=0), \
                patch("expansion_policies.force_replace", return_value=False):
            play(game, 0, "examine", 1, challenger=2)
        self.assertEqual(len(game.players[2].cards), 1)
        self.assertEqual(len(game.players[0].cards), 2)
        self.assertEqual(game.observation(0)["inspected"], ((1, "captain"),))

    def test_forced_examine_draws_before_returning_shown_card(self):
        game = arranged([("inquisitor", "duke"), ("captain", "captain"),
                         ("captain", "assassin"), ("duke", "contessa")])
        draws = []
        class WatchedDeck(list):
            def pop(self, index=-1):
                draws.append(Counter(self))
                return super().pop(index)
        game.deck = WatchedDeck(game.deck)
        with patch("expansion_policies.show_index", return_value=0), \
                patch("expansion_policies.force_replace", return_value=True):
            game._examine(0, 1)
        self.assertEqual(len(draws), 1)
        self.assertEqual(draws[0]["captain"], 0)
        self.assertEqual(game.players[1].cards.count("captain"), 1)
        self.assertEqual(Counter(game.deck)["captain"], 1)
        self.assertEqual(game.observation(0)["inspected"], ())
        game.check_invariants()

    def test_exchange_invalidates_previous_private_inspection(self):
        game = arranged(normal_hands())
        with patch("expansion_policies.show_index", return_value=1), \
                patch("expansion_policies.force_replace", return_value=False):
            game._examine(0, 1)
        self.assertTrue(game.observation(0)["inspected"])
        with patch("expansion_policies.keep_indices", return_value=[0, 1]):
            game._exchange(1, 1)
        self.assertEqual(game.observation(0)["inspected"], ())
        game.check_invariants()

    def test_lost_card_invalidates_previous_private_inspection(self):
        game = arranged(normal_hands())
        with patch("expansion_policies.show_index", return_value=1), \
                patch("expansion_policies.force_replace", return_value=False):
            game._examine(0, 1)
        game._lose(1)
        self.assertEqual(game.observation(0)["inspected"], ())
        game.check_invariants()

    def test_negative_proof_returns_whole_hand_before_either_replacement(self):
        game = arranged([("captain", "captain"), ("duke", "contessa"),
                         ("inquisitor", "duke"), ("assassin", "inquisitor")])
        draws = []
        class WatchedDeck(list):
            def pop(self, index=-1):
                draws.append((Counter(self), len(game.players[1].cards)))
                return super().pop(index)
        game.deck = WatchedDeck(game.deck)
        self.assertTrue(game.resolve_claim(0, "duke", 1, negative=True))
        self.assertEqual(len(draws), 2)
        self.assertEqual(draws[0][0]["captain"], 3)
        self.assertEqual([entry[1] for entry in draws], [1, 1])
        self.assertEqual(len(game.players[0].cards), 2)
        game.check_invariants()

    def test_inquisitor_blocks_steal_as_target(self):
        game = arranged(normal_hands())
        play(game, 1, "steal", 2, block=(2, "inquisitor"))
        self.assertEqual(game.players[1].coins, 2)
        self.assertEqual(game.players[2].coins, 2)

    def test_third_party_cannot_block_steal_with_inquisitor(self):
        game = arranged(normal_hands())
        def third_party_block(view, *args, **kwargs):
            return "inquisitor" if view["self"] == 2 else None
        with patch.object(game, "_challenger", return_value=None), \
                patch("expansion_policies.choose_block", side_effect=third_party_block):
            game.step(1, Action("steal", 0))
        self.assertEqual(game.players[1].coins, 4)
        self.assertEqual(game.players[0].coins, 0)
        game.check_invariants()


class ReproducibilityAndSequenceTests(TestCase):
    def test_decision_randomness_does_not_perturb_card_draws(self):
        left = arranged(normal_hands())
        right = arranged(normal_hands())
        for _ in range(1000):
            left.decision_rngs[0].random()
        with patch("expansion_policies.keep_indices", return_value=[0, 1]):
            left._exchange(0, 1)
            right._exchange(0, 1)
        self.assertEqual(left.players[0].cards, right.players[0].cards)
        self.assertEqual(left.deck, right.deck)
        left.check_invariants()
        right.check_invariants()

    def test_decision_streams_follow_identities_through_seat_rotation(self):
        left = ExpansionGame(4, 91, ["balanced"] * 4)
        identities = [1, 2, 3, 0]
        right = ExpansionGame(4, 91, ["balanced"] * 4, identities=identities)
        self.assertEqual(left.deck, right.deck)
        for seat, identity in enumerate(identities):
            self.assertEqual([left.decision_rngs[identity].random() for _ in range(5)],
                             [right.decision_rngs[seat].random() for _ in range(5)])

    def test_seeded_legal_sequences_preserve_cards_coins_and_elimination(self):
        # Responses remain policy controlled; action selection covers legal
        # bluff, conversion and inspection paths independently of policy scores.
        actions_seen = set()
        for profile in PROFILES:
            for n in range(2, 11):
                for seed in range(4):
                    with self.subTest(profile=profile, players=n, seed=seed):
                        game = ExpansionGame(n, 5000 + seed, ["balanced"] * n,
                                             profile=profile, max_turns=300, strict=True)
                        choice_rng = Random(70000 + 100 * n + seed)
                        for turn in range(300):
                            if sum(p.alive for p in game.players) <= 1:
                                break
                            actor = turn % n
                            if not game.players[actor].alive:
                                continue
                            legal = game.available_actions(actor)
                            self.assertTrue(legal)
                            action = choice_rng.choice(legal)
                            actions_seen.add(action.kind)
                            game.step(actor, action)
                            game.check_invariants()
                            self.assertTrue(all(p.coins == 0 for p in game.players if not p.alive))
                        game.check_invariants()
        self.assertTrue({"convert_self", "convert_other", "embezzle", "examine",
                         "exchange", "steal", "assassinate", "coup"} <= actions_seen)


if __name__ == "__main__":
    main()
