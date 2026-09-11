import pytest
from game import engine, manager
from models import Game


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(manager.socketio, "sleep", lambda s: None)
    # `apply_action` schedules the bot's turn on a background thread. Left
    # alone, that thread outlives the test and keeps using the test's
    # SQLAlchemy session and monkeypatched dice, which surfaces as
    # PytestUnhandledThreadExceptionWarning/StopIteration noise from
    # whichever test happens to run next. The tests that actually want a
    # bot turn call `manager._run_bot_turn(...)` directly and synchronously,
    # so stubbing the scheduler out costs no coverage.
    monkeypatch.setattr(manager.socketio, "start_background_task", lambda fn, *a, **kw: None)


def test_create_bot_game_persists_fresh_state(app, make_user):
    user = make_user()
    game = manager.create_bot_game(user.id)
    assert game.mode == "bot"
    assert game.status == "active"
    assert game.state_json["center"] == list(range(21, 37))


def test_apply_action_rejects_non_player(app, make_user):
    user = make_user()
    game = manager.create_bot_game(user.id)
    state, error = manager.apply_action(game.id, 999999, "roll")
    assert state is None
    assert "not a player" in error


def test_full_human_turn_claims_a_tile(app, make_user, monkeypatch):
    seq = iter([5, 5, 5, 5, "w", "w", 1, 2, "w", "w", 3, 4])
    monkeypatch.setattr(engine.random, "choice", lambda faces: next(seq))

    user = make_user()
    game = manager.create_bot_game(user.id)

    state, error = manager.apply_action(game.id, user.id, "roll")
    assert error is None
    assert state["roll"] == [5, 5, 5, 5, "w", "w", 1, 2]

    state, error = manager.apply_action(game.id, user.id, "pick", {"face": 5})
    assert error is None
    assert state["aside"] == [5, 5, 5, 5]

    state, error = manager.apply_action(game.id, user.id, "roll")
    assert error is None
    assert state["roll"] == ["w", "w", 3, 4]

    state, error = manager.apply_action(game.id, user.id, "pick", {"face": "w"})
    assert error is None
    assert state["aside"] == [5, 5, 5, 5, "w", "w"]

    state, error = manager.apply_action(game.id, user.id, "claim", {"kind": "take", "num": 30})
    assert error is None
    assert state["stacks"][0] == [30]
    assert state["turn"] == 1
    assert state["player1_id"] == user.id


def test_resign_finalizes_game_as_a_loss(app, make_user):
    alice = make_user(email="a@example.com", display_name="Alice")
    bob = make_user(email="b@example.com", display_name="Bob")
    game = manager.create_pvp_game(alice.id, bob.id)

    state, error = manager.apply_action(game.id, alice.id, "resign")
    assert error is None
    assert state["result"]["winner"] == 1
    assert state["status"] == "resigned"


def test_roll_into_dead_end_auto_busts_instead_of_stalling(app, make_user, monkeypatch):
    # First roll gives six 1s plus two other faces; picking 1 leaves aside
    # with six 1s. Second roll (2 dice, since 8-6=2) comes back with only
    # more 1s -- a face already set aside, so selectable(state) is empty
    # and the player has no legal move. This must auto-bust the turn
    # instead of leaving the player stuck (can't pick, can't roll, can't
    # stop -- only resign).
    seq = iter([1, 1, 1, 1, 1, 1, 5, 2, 1, 1])
    monkeypatch.setattr(engine.random, "choice", lambda faces: next(seq))

    user = make_user()
    game = manager.create_bot_game(user.id)

    state, error = manager.apply_action(game.id, user.id, "roll")
    assert error is None
    assert state["roll"] == [1, 1, 1, 1, 1, 1, 5, 2]

    state, error = manager.apply_action(game.id, user.id, "pick", {"face": 1})
    assert error is None
    assert state["aside"] == [1, 1, 1, 1, 1, 1]

    state, error = manager.apply_action(game.id, user.id, "roll")
    assert error is None
    assert state["roll"] == []
    assert state["aside"] == []
    assert state["turn"] == 1
    assert "busted" in state["log"][0]["text"]


def test_bot_turn_runs_to_completion_and_claims_a_tile(app, make_user, monkeypatch, db):
    seq = iter([5, 5, 5, 5, 5, 5, 5, "w", "w"])
    monkeypatch.setattr(engine.random, "choice", lambda faces: next(seq))

    user = make_user()
    game = manager.create_bot_game(user.id)
    game.state_json = {**game.state_json, "turn": 1}
    db.session.add(game)
    db.session.commit()

    manager._run_bot_turn(game.id, speed=0)

    refreshed = db.session.get(Game, game.id)
    assert 36 in refreshed.state_json["stacks"][1]
    assert refreshed.state_json["turn"] == 0
