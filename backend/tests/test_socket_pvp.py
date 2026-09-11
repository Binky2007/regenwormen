from flask_jwt_extended import create_access_token
from extensions import socketio
from game import matchmaking


def _token_for(app, user):
    with app.app_context():
        return create_access_token(identity=str(user.id))


def test_find_match_pairs_two_waiting_players(app, make_user, monkeypatch):
    matchmaking.clear()
    from game import manager
    monkeypatch.setattr(manager.socketio, "sleep", lambda s: None)

    alice = make_user(email="a@example.com", display_name="Alice")
    bob = make_user(email="b@example.com", display_name="Bob")
    client_a = socketio.test_client(app, namespace="/game", auth={"token": _token_for(app, alice)})
    client_b = socketio.test_client(app, namespace="/game", auth={"token": _token_for(app, bob)})

    client_a.emit("find_match", namespace="/game")
    assert not any(m["name"] == "match_found" for m in client_a.get_received(namespace="/game"))

    client_b.emit("find_match", namespace="/game")
    received_b = client_b.get_received(namespace="/game")
    assert any(m["name"] == "match_found" for m in received_b)
    assert any(m["name"] == "game_state" for m in received_b)
