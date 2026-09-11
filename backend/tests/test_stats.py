from extensions import db
from models import Game, GameResult
from flask_jwt_extended import create_access_token
from game import engine, manager


def _finish_game(winner, loser, worms_winner=10, worms_loser=4, best_turn=27):
    game = Game(mode="bot", player1_id=winner.id, player2_id=None, status="finished", state_json={})
    db.session.add(game)
    db.session.commit()
    db.session.add(GameResult(game_id=game.id, user_id=winner.id, worms=worms_winner, tiles_won=[30], is_winner=True, best_turn_score=best_turn))
    db.session.add(GameResult(game_id=game.id, user_id=loser.id, worms=worms_loser, tiles_won=[22], is_winner=False, best_turn_score=22))
    db.session.commit()


def test_leaderboard_orders_by_worms_desc(app, client, make_user):
    alice = make_user(email="a@example.com", display_name="Alice")
    bob = make_user(email="b@example.com", display_name="Bob")
    _finish_game(alice, bob)

    res = client.get("/api/leaderboard")
    assert res.status_code == 200
    names = [row["name"] for row in res.get_json()]
    assert names[0] == "Alice"


def test_profile_requires_auth(client):
    res = client.get("/api/profile")
    assert res.status_code == 401


def test_profile_returns_own_stats(app, client, make_user):
    alice = make_user(email="a@example.com", display_name="Alice")
    bob = make_user(email="b@example.com", display_name="Bob")
    _finish_game(alice, bob, worms_winner=15, best_turn=30)
    with app.app_context():
        token = create_access_token(identity=str(alice.id))

    res = client.get("/api/profile", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.get_json()
    assert body["worms"] == 15
    assert body["games"] == 1
    assert body["win_rate"] == 100
    assert body["best_turn"] == 30


def test_a_finished_game_feeds_the_leaderboard_and_profile(app, client, make_user, monkeypatch):
    """End to end: real gameplay -> GameResult rows -> the stats endpoints.

    The other tests in this file hand-write GameResult rows, so nothing
    checked that the numbers a real game produces are the numbers the API
    reports. This plays an actual game through `apply_action` and then reads
    the endpoints. Only the last tile is left in the middle so the game ends
    in one turn -- everything else (rolling, setting dice aside, claiming,
    detecting the end, recording results) is the real code path.
    """
    monkeypatch.setattr(manager.socketio, "sleep", lambda s: None)
    monkeypatch.setattr(manager.socketio, "start_background_task", lambda fn, *a, **kw: None)
    seq = iter([5, 5, 5, 5, "w", "w", 1, 2, "w", "w", 3, 4])
    monkeypatch.setattr(engine.random, "choice", lambda faces: next(seq))

    alice = make_user(email="a@example.com", display_name="Alice")
    game = manager.create_bot_game(alice.id)
    game.state_json = {**game.state_json, "center": [21]}
    db.session.add(game)
    db.session.commit()

    for action, payload in [("roll", None), ("pick", {"face": 5}), ("roll", None), ("pick", {"face": "w"})]:
        state, error = manager.apply_action(game.id, alice.id, action, payload)
        assert error is None, error
    state, error = manager.apply_action(game.id, alice.id, "claim", {"kind": "take", "num": 21})
    assert error is None, error

    # Six dice worth 30 points bought tile 21, which carries one worm.
    assert state["result"] == {"winner": 0, "worms": [1, 0]}
    assert db.session.get(Game, game.id).status == "finished"
    rows = GameResult.query.filter_by(game_id=game.id).all()
    assert len(rows) == 1  # the bot has no user row of its own
    assert (rows[0].user_id, rows[0].worms, rows[0].tiles_won, rows[0].is_winner, rows[0].best_turn_score) \
        == (alice.id, 1, [21], True, 30)

    board = client.get("/api/leaderboard").get_json()
    assert [(r["name"], r["games"], r["worms"]) for r in board] == [("Alice", 1, 1)]

    with app.app_context():
        token = create_access_token(identity=str(alice.id))
    profile = client.get("/api/profile", headers={"Authorization": f"Bearer {token}"}).get_json()
    assert profile == {"games": 1, "worms": 1, "win_rate": 100, "best_turn": 30}
