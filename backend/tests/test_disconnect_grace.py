from flask_jwt_extended import create_access_token
from extensions import db, socketio
from models import Game
from game import manager, socket_handlers


def test_disconnect_grace_auto_resigns_if_not_reconnected(app, make_user, monkeypatch):
    monkeypatch.setattr(manager.socketio, "sleep", lambda s: None)
    alice = make_user(email="a@example.com", display_name="Alice")
    bob = make_user(email="b@example.com", display_name="Bob")
    game = manager.create_pvp_game(alice.id, bob.id)

    manager._disconnect_grace(game.id, alice.id, lambda: False)

    refreshed = db.session.get(Game, game.id)
    assert refreshed.status == "resigned"
    assert refreshed.state_json["result"]["winner"] == 1


def test_disconnect_grace_noop_if_reconnected(app, make_user, monkeypatch):
    monkeypatch.setattr(manager.socketio, "sleep", lambda s: None)
    alice = make_user(email="a2@example.com", display_name="Alice2")
    bob = make_user(email="b2@example.com", display_name="Bob2")
    game = manager.create_pvp_game(alice.id, bob.id)

    manager._disconnect_grace(game.id, alice.id, lambda: True)

    refreshed = db.session.get(Game, game.id)
    assert refreshed.status == "active"


def test_closing_a_second_tab_does_not_endanger_the_live_game(app, make_user, monkeypatch):
    """Presence is per connection: one tab closing is not a disconnect."""
    scheduled = []
    monkeypatch.setattr(manager, "schedule_disconnect_grace", lambda *a: scheduled.append(a))
    monkeypatch.setattr(manager.socketio, "sleep", lambda s: None)
    alice = make_user(email="a3@example.com", display_name="Alice3")
    bob = make_user(email="b3@example.com", display_name="Bob3")
    game = manager.create_pvp_game(alice.id, bob.id)
    with app.app_context():
        token = create_access_token(identity=str(alice.id))

    playing_tab = socketio.test_client(app, namespace="/game", auth={"token": token})
    other_tab = socketio.test_client(app, namespace="/game", auth={"token": token})

    other_tab.disconnect(namespace="/game")
    assert socket_handlers.is_user_connected(alice.id)
    assert scheduled == []

    playing_tab.disconnect(namespace="/game")
    assert not socket_handlers.is_user_connected(alice.id)
    assert [args[0] for args in scheduled] == [game.id]
    assert scheduled[0][2]() is False


def test_closing_a_second_tab_leaves_the_other_tab_queued(app, make_user):
    from game import matchmaking

    matchmaking.clear()
    alice = make_user(email="a4@example.com", display_name="Alice4")
    with app.app_context():
        token = create_access_token(identity=str(alice.id))

    queued_tab = socketio.test_client(app, namespace="/game", auth={"token": token})
    other_tab = socketio.test_client(app, namespace="/game", auth={"token": token})
    queued_tab.emit("find_match", namespace="/game")

    other_tab.disconnect(namespace="/game")

    assert [u for u, _ in matchmaking._queue] == [alice.id]
    queued_tab.disconnect(namespace="/game")
    assert matchmaking._queue == []
