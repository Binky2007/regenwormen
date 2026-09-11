from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, desc
from extensions import db
from models import GameResult, User

stats_bp = Blueprint("stats", __name__)


def _aggregate(user_id=None):
    q = (
        db.session.query(
            User.id, User.display_name,
            func.coalesce(func.sum(GameResult.worms), 0).label("worms"),
            func.count(GameResult.id).label("games"),
            func.coalesce(func.sum(GameResult.is_winner), 0).label("wins"),
            func.coalesce(func.max(GameResult.best_turn_score), 0).label("best_turn"),
        )
        .outerjoin(GameResult, GameResult.user_id == User.id)
        .group_by(User.id)
    )
    if user_id is not None:
        q = q.filter(User.id == user_id)
    return q


@stats_bp.get("/leaderboard")
def leaderboard():
    rows = _aggregate().order_by(desc("worms")).all()
    return jsonify([
        {"rank": i + 1, "name": r.display_name, "games": r.games, "worms": int(r.worms)}
        for i, r in enumerate(rows)
    ])


@stats_bp.get("/profile")
@jwt_required()
def profile():
    user_id = int(get_jwt_identity())
    row = _aggregate(user_id).first()
    if row is None:
        return jsonify({"error": "user not found"}), 404
    win_rate = round(100 * row.wins / row.games) if row.games else 0
    return jsonify({
        "games": row.games, "worms": int(row.worms),
        "win_rate": win_rate, "best_turn": int(row.best_turn),
    })
