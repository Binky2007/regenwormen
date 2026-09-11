from datetime import datetime
from extensions import db


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Game(db.Model):
    __tablename__ = "games"
    id = db.Column(db.Integer, primary_key=True)
    mode = db.Column(db.Enum("bot", "pvp", name="game_mode"), nullable=False)
    player1_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    player2_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    status = db.Column(db.Enum("active", "finished", "resigned", name="game_status"), nullable=False, default="active")
    state_json = db.Column(db.JSON, nullable=False)
    winner = db.Column(db.Enum("player1", "player2", "draw", name="game_winner"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    finished_at = db.Column(db.DateTime, nullable=True)


class GameResult(db.Model):
    __tablename__ = "game_results"
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    worms = db.Column(db.Integer, nullable=False)
    tiles_won = db.Column(db.JSON, nullable=False)
    is_winner = db.Column(db.Boolean, nullable=False)
    best_turn_score = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
