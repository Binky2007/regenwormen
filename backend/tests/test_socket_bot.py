import pytest
from flask_jwt_extended import create_access_token
from extensions import socketio


def _token_for(app, user):
    with app.app_context():
        return create_access_token(identity=str(user.id))


def _states(client):
    return [m["args"][0] for m in client.get_received(namespace="/game") if m["name"] == "game_state"]


@pytest.fixture
def no_background(monkeypatch):
    """Keep the bot loop off real threads, but record that it was scheduled."""
    from game import manager
    calls = []
    monkeypatch.setattr(manager.socketio, "sleep", lambda s: None)
    monkeypatch.setattr(
        manager.socketio, "start_background_task",
        lambda fn, *a, **kw: calls.append((fn, a)),
    )
    return calls


def test_connect_without_token_is_refused(app):
    client = socketio.test_client(app, namespace="/game")
    assert not client.is_connected(namespace="/game")


def test_start_bot_game_returns_initial_state(app, make_user, monkeypatch):
    from game import manager
    monkeypatch.setattr(manager.socketio, "sleep", lambda s: None)
    user = make_user()
    token = _token_for(app, user)
    client = socketio.test_client(app, namespace="/game", auth={"token": token})
    assert client.is_connected(namespace="/game")

    client.emit("start_bot_game", namespace="/game")
    received = client.get_received(namespace="/game")
    states = [m for m in received if m["name"] == "game_state"]
    assert states
    payload = states[0]["args"][0]
    assert payload["center"] == list(range(21, 37))
    assert payload["turn"] == 0


def test_action_rejects_illegal_move(app, make_user, monkeypatch):
    from game import manager
    monkeypatch.setattr(manager.socketio, "sleep", lambda s: None)
    user = make_user()
    token = _token_for(app, user)
    client = socketio.test_client(app, namespace="/game", auth={"token": token})
    client.emit("start_bot_game", namespace="/game")
    game_id = [m for m in client.get_received(namespace="/game") if m["name"] == "game_state"][0]["args"][0]["game_id"]

    client.emit("action", {"game_id": game_id, "type": "pick", "payload": {"face": 5}}, namespace="/game")
    received = client.get_received(namespace="/game")
    errors = [m for m in received if m["name"] == "error"]
    assert errors
    assert "not selectable" in errors[0]["args"][0]["message"]


def test_reconnecting_client_resumes_its_game_without_starting_a_new_one(app, make_user, no_background):
    """A refreshed browser gets its game back from the server, not a new one."""
    from models import Game

    user = make_user()
    token = _token_for(app, user)

    first = socketio.test_client(app, namespace="/game", auth={"token": token})
    first.emit("start_bot_game", namespace="/game")
    game_id = _states(first)[0]["game_id"]
    first.emit("action", {"game_id": game_id, "type": "roll"}, namespace="/game")
    rolled = _states(first)[-1]
    assert rolled["roll"], "expected dice on the table before the refresh"
    first.disconnect(namespace="/game")

    # A page refresh: a brand new socket, same user, no game id in hand.
    second = socketio.test_client(app, namespace="/game", auth={"token": token})
    second.get_received(namespace="/game")
    second.emit("resume_game", namespace="/game")

    states = _states(second)
    assert len(states) == 1
    assert states[0]["game_id"] == game_id
    assert states[0]["roll"] == rolled["roll"]
    assert states[0]["aside"] == rolled["aside"]
    assert Game.query.count() == 1

    # And the resumed socket is back in the game's room, so a later action
    # broadcast reaches it.
    second.emit("action", {"game_id": game_id, "type": "pick", "payload": {"face": rolled["roll"][0]}}, namespace="/game")
    assert _states(second)


def test_resume_game_is_silent_when_the_user_has_no_active_game(app, make_user, no_background):
    user = make_user()
    client = socketio.test_client(app, namespace="/game", auth={"token": _token_for(app, user)})
    client.get_received(namespace="/game")

    client.emit("resume_game", namespace="/game")

    assert _states(client) == []


def test_resume_game_ignores_a_finished_game(app, make_user, no_background, db):
    from game import manager
    from models import Game

    user = make_user()
    game = manager.create_bot_game(user.id)
    game.status = "finished"
    db.session.add(game)
    db.session.commit()

    client = socketio.test_client(app, namespace="/game", auth={"token": _token_for(app, user)})
    client.get_received(namespace="/game")
    client.emit("resume_game", namespace="/game")

    assert _states(client) == []
    assert db.session.get(Game, game.id).status == "finished"


def test_resume_reschedules_the_bot_turn_after_a_backend_restart(app, make_user, no_background, db):
    from game import manager
    from models import Game

    user = make_user()
    game = manager.create_bot_game(user.id)
    game.state_json = {**game.state_json, "turn": 1}
    db.session.add(game)
    db.session.commit()
    # A restarted process has no in-memory runtime tracking left, so the
    # bot loop for this game is gone even though the DB row is still active.
    manager._runtime.clear()
    no_background.clear()

    client = socketio.test_client(app, namespace="/game", auth={"token": _token_for(app, user)})
    client.get_received(namespace="/game")
    client.emit("resume_game", namespace="/game")

    assert _states(client)[0]["game_id"] == game.id
    assert [(fn, args) for fn, args in no_background] == [(manager._run_bot_turn, (game.id,))]


def test_resume_does_not_double_schedule_a_running_bot_turn(app, make_user, no_background, db):
    from game import manager

    user = make_user()
    game = manager.create_bot_game(user.id)
    game.state_json = {**game.state_json, "turn": 1}
    db.session.add(game)
    db.session.commit()
    manager._runtime_for(game.id)["bot_running"] = True
    no_background.clear()

    client = socketio.test_client(app, namespace="/game", auth={"token": _token_for(app, user)})
    client.get_received(namespace="/game")
    client.emit("resume_game", namespace="/game")

    assert _states(client)[0]["game_id"] == game.id
    assert no_background == []
