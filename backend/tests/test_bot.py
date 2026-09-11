from game.engine import fresh_game
from game.bot import bot_value, choose_bot_face


def test_bot_value_prefers_worms_with_bonus():
    state = fresh_game()
    state["roll"] = ["w", "w", 5, 5, 5]
    assert bot_value(state, "w") == 2 * 5 + 8
    assert bot_value(state, 5) == 15


def test_choose_bot_face_picks_highest_value():
    state = fresh_game()
    state["roll"] = [1, 1, "w"]
    assert choose_bot_face(state) == "w"


def test_choose_bot_face_returns_none_when_nothing_selectable():
    state = fresh_game()
    state["roll"] = [3, 3]
    state["aside"] = [3, 3, 3]
    assert choose_bot_face(state) is None
