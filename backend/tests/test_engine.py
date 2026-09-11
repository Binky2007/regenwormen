from game.engine import (
    fresh_game, score, selectable, options, roll_into, pick_into,
    bust_into, claim_into, end_turn, worms_on, val,
)


def test_worms_on_boundaries():
    assert worms_on(21) == 1
    assert worms_on(24) == 1
    assert worms_on(25) == 2
    assert worms_on(28) == 2
    assert worms_on(29) == 3
    assert worms_on(32) == 3
    assert worms_on(33) == 4
    assert worms_on(36) == 4


def test_val():
    assert val(3) == 3
    assert val("w") == 5


def test_score_sums_worms_as_five():
    assert score([3, 3, "w", "w"]) == 16


def test_selectable_excludes_already_used_faces():
    state = fresh_game()
    state["roll"] = [3, 3, 5, "w"]
    state["aside"] = [5, 5]
    assert selectable(state) == [3, "w"]


def test_options_requires_worm_and_min_21():
    state = fresh_game()
    state["aside"] = [4, 4, 4]
    assert options(state, score(state["aside"])) == []
    state["aside"] = [5, 5, 5, 5, "w"]
    sc = score(state["aside"])
    assert sc == 25
    assert options(state, sc) == [{"kind": "take", "num": 25}]


def test_options_offers_steal_when_top_tile_matches():
    state = fresh_game()
    state["aside"] = ["w", "w", "w", "w", "w", 5]
    sc = score(state["aside"])
    assert sc == 30
    state["stacks"][1] = [30]
    opts = options(state, sc)
    assert {"kind": "steal", "num": 30} in opts


def test_roll_into_fills_remaining_dice():
    state = fresh_game()
    state["aside"] = [5, 5]
    state = roll_into(state)
    assert len(state["roll"]) == 6
    assert all(f in (1, 2, 3, 4, 5, "w") for f in state["roll"])


def test_pick_into_moves_matching_dice_to_aside_and_logs():
    state = fresh_game()
    state["roll"] = [4, 4, 3, "w"]
    state = pick_into(state, 4, "Alice")
    assert state["aside"] == [4, 4]
    assert state["roll"] == []
    assert "Alice set aside 2" in state["log"][0]["text"]


def test_bust_into_returns_top_tile_and_ends_turn():
    state = fresh_game()
    state["stacks"][0] = [24, 30]
    state = bust_into(state, "Alice", "no new value")
    assert 30 in state["center"]
    assert state["stacks"][0] == [24]
    assert state["turn"] == 1
    assert "busted" in state["log"][0]["text"]


def test_bust_into_with_no_tiles_just_ends_turn():
    state = fresh_game()
    state = bust_into(state, "Alice")
    assert state["turn"] == 1
    assert state["stacks"][0] == []


def test_claim_into_take_removes_tile_from_center_and_tracks_best_score():
    state = fresh_game()
    state["aside"] = [5, 5, 5, 5, "w"]
    state = claim_into(state, {"kind": "take", "num": 25}, "Alice")
    assert 25 not in state["center"]
    assert state["stacks"][0] == [25]
    assert state["best_scores"][0] == 25
    assert state["turn"] == 1


def test_claim_into_steal_moves_tile_between_stacks():
    state = fresh_game()
    state["stacks"][1] = [22, 28]
    state["aside"] = [5, 5, 5, 5, "w"]
    state = claim_into(state, {"kind": "steal", "num": 28}, "Alice")
    assert state["stacks"][1] == [22]
    assert state["stacks"][0] == [28]


def test_end_turn_finishes_game_when_center_empty():
    state = fresh_game()
    state["center"] = []
    state["stacks"] = [[21, 25], [36]]
    state = end_turn(state)
    assert state["result"]["winner"] == 1
    assert state["result"]["worms"] == [3, 4]
