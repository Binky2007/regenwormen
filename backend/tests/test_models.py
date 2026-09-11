from models import User, Game, GameResult


def test_create_user_game_and_result(app, db):
    user1 = User(email="a@example.com", password_hash="x", display_name="Alice")
    user2 = User(email="b@example.com", password_hash="x", display_name="Bob")
    db.session.add_all([user1, user2])
    db.session.commit()

    game = Game(mode="bot", player1_id=user1.id, player2_id=None, status="active", state_json={"turn": 0})
    db.session.add(game)
    db.session.commit()
    assert game.id is not None
    assert game.status == "active"

    result = GameResult(game_id=game.id, user_id=user1.id, worms=5, tiles_won=[24], is_winner=True, best_turn_score=24)
    db.session.add(result)
    db.session.commit()
    assert result.id is not None
