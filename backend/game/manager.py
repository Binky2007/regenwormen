from contextlib import nullcontext
from datetime import datetime
from flask import has_app_context
from extensions import db, socketio
from models import Game, GameResult, User
from game.engine import (
    fresh_game, roll_into, pick_into, bust_into, claim_into,
    selectable, options, score, worms_on,
)
from game.bot import choose_bot_face

BOT_NAME = "Bot Wurm"
DISCONNECT_GRACE_SECONDS = 30

_app = None
_runtime = {}


def init_app(app):
    global _app
    _app = app


def _runtime_for(game_id):
    return _runtime.setdefault(game_id, {"bot_running": False})


def _actor_name(game, idx):
    if game.mode == "bot" and idx == 1:
        return BOT_NAME
    user_id = game.player1_id if idx == 0 else game.player2_id
    user = db.session.get(User, user_id) if user_id else None
    return user.display_name if user else "Unknown"


def _player_index(game, user_id):
    if game.player1_id == user_id:
        return 0
    if game.player2_id == user_id:
        return 1
    return None


def create_bot_game(user_id):
    game = Game(mode="bot", player1_id=user_id, player2_id=None, status="active", state_json=fresh_game())
    db.session.add(game)
    db.session.commit()
    _runtime_for(game.id)
    return game


def create_pvp_game(user1_id, user2_id):
    game = Game(mode="pvp", player1_id=user1_id, player2_id=user2_id, status="active", state_json=fresh_game())
    db.session.add(game)
    db.session.commit()
    _runtime_for(game.id)
    return game


def serialize(game):
    state = dict(game.state_json)
    return {
        "game_id": game.id,
        "mode": game.mode,
        "status": game.status,
        "player1_id": game.player1_id,
        "player2_id": game.player2_id,
        "player1_name": _actor_name(game, 0),
        "player2_name": _actor_name(game, 1),
        **state,
    }


def _save(game, state):
    game.state_json = state
    db.session.add(game)
    db.session.commit()


def _record_results(game, state):
    game.finished_at = datetime.utcnow()
    game.winner = (
        "draw" if state["result"]["winner"] is None
        else "player1" if state["result"]["winner"] == 0 else "player2"
    )
    db.session.add(game)
    for idx, user_id in enumerate([game.player1_id, game.player2_id]):
        if user_id is None:
            continue
        db.session.add(GameResult(
            game_id=game.id, user_id=user_id,
            worms=state["result"]["worms"][idx],
            tiles_won=state["stacks"][idx],
            is_winner=(state["result"]["winner"] == idx),
            best_turn_score=state["best_scores"][idx],
        ))
    db.session.commit()


def _finalize_resign(game, state, resigned_by):
    worms = [sum(worms_on(n) for n in s) for s in state["stacks"]]
    winner = 1 - resigned_by
    state["result"] = {"winner": winner, "worms": worms, "resigned_by": resigned_by}
    game.status = "resigned"
    _save(game, state)
    _record_results(game, state)
    return serialize(game)


def apply_action(game_id, user_id, action_type, payload=None):
    payload = payload or {}
    game = db.session.get(Game, game_id)
    if game is None or game.status != "active":
        return None, "game not found or already finished"
    idx = _player_index(game, user_id)
    if idx is None:
        return None, "you are not a player in this game"

    state = dict(game.state_json)

    if action_type == "resign":
        return _finalize_resign(game, state, resigned_by=idx), None

    if state["turn"] != idx:
        return None, "not your turn"

    name = _actor_name(game, idx)

    if action_type == "roll":
        if state["roll"] or len(state["aside"]) >= 8:
            return None, "cannot roll right now"
        state = roll_into(state)
        if not selectable(state):
            state = bust_into(state, name, "no new value")
    elif action_type == "pick":
        face = payload.get("face")
        if face not in selectable(state):
            return None, "that value is not selectable"
        state = pick_into(state, face, name)
    elif action_type == "claim":
        sc = score(state["aside"])
        opts = options(state, sc)
        match = next((o for o in opts if o["kind"] == payload.get("kind") and o["num"] == payload.get("num")), None)
        if match is None:
            return None, "that claim is not available"
        state = claim_into(state, match, name)
    elif action_type == "stop":
        if state["roll"] or not state["aside"]:
            return None, "nothing to stop"
        sc = score(state["aside"])
        opts = options(state, sc)
        state = claim_into(state, opts[0], name) if opts else bust_into(state, name, "nothing to claim")
    else:
        return None, "unknown action"

    game.status = "finished" if state["result"] is not None else game.status
    _save(game, state)

    if state["result"] is not None:
        _record_results(game, state)
    elif game.mode == "bot" and state["turn"] == 1:
        _schedule_bot_turn(game.id)

    return serialize(game), None


def active_pvp_game_ids_for_user(user_id):
    games = Game.query.filter(
        Game.mode == "pvp", Game.status == "active",
        db.or_(Game.player1_id == user_id, Game.player2_id == user_id),
    ).all()
    return [g.id for g in games]


def latest_active_game_for_user(user_id):
    """The game a reconnecting client should be put back into.

    Nothing ever retires an abandoned game, so a user can accumulate several
    rows with status 'active'. Only the newest one is the game they were
    actually playing, so that is the single one we resume -- resuming all of
    them would leave the client's board flipping between old games as their
    bot loops emit.
    """
    return (
        Game.query.filter(
            Game.status == "active",
            db.or_(Game.player1_id == user_id, Game.player2_id == user_id),
        )
        .order_by(Game.id.desc())
        .first()
    )


def resume_active_game(user_id):
    """Serialize the user's in-progress game, restarting the bot if needed.

    `state_json` holds the whole engine state, so a client that refreshed --
    or a backend that restarted -- can pick the game straight back up. The
    in-memory bot loop does not survive a restart, so a bot game caught on
    the bot's turn gets its turn rescheduled here; `_schedule_bot_turn` is
    idempotent, so a loop that is still running is left alone.
    """
    game = latest_active_game_for_user(user_id)
    if game is None:
        return None
    if game.mode == "bot" and game.state_json["turn"] == 1:
        _schedule_bot_turn(game.id)
    return serialize(game)


def _schedule_bot_turn(game_id):
    rt = _runtime_for(game_id)
    if rt["bot_running"]:
        return
    rt["bot_running"] = True
    socketio.start_background_task(_run_bot_turn, game_id)


def _app_context():
    # In production this runs on a real background thread with no ambient
    # Flask app context, so we push one. Tests call this function directly
    # (synchronously) from inside a test's own `with app.app_context():`
    # block; pushing a *second, nested* context there would give
    # Flask-SQLAlchemy a distinct scoped Session (it scopes by
    # id(app_ctx)), whose commits would be invisible to the outer test
    # session's identity map. Reuse the ambient context when one exists.
    return nullcontext() if has_app_context() else _app.app_context()


def _run_bot_turn(game_id, speed=0.7):
    rt = _runtime_for(game_id)
    with _app_context():
        try:
            while True:
                socketio.sleep(speed)
                game = db.session.get(Game, game_id)
                if game is None or game.status != "active" or game.state_json["turn"] != 1:
                    return
                state = dict(game.state_json)
                state = roll_into(state)
                _save(game, state)
                socketio.emit("game_state", serialize(game), room=f"game:{game_id}", namespace="/game")

                socketio.sleep(speed)
                state = dict(db.session.get(Game, game_id).state_json)
                face = choose_bot_face(state)
                if face is None:
                    state = bust_into(state, BOT_NAME, "no new value")
                    game.status = "finished" if state["result"] is not None else game.status
                    _save(game, state)
                    socketio.emit("game_state", serialize(game), room=f"game:{game_id}", namespace="/game")
                    if state["result"] is not None:
                        _record_results(game, state)
                        return
                    continue
                state = pick_into(state, face, BOT_NAME)
                _save(game, state)
                socketio.emit("game_state", serialize(game), room=f"game:{game_id}", namespace="/game")

                socketio.sleep(speed)
                state = dict(db.session.get(Game, game_id).state_json)
                sc = score(state["aside"])
                opts = options(state, sc)
                must_stop = len(state["aside"]) >= 8
                if opts and (must_stop or sc >= 27 or len(state["aside"]) >= 6):
                    state = claim_into(state, opts[0], BOT_NAME)
                elif must_stop:
                    state = bust_into(state, BOT_NAME, "out of dice")
                else:
                    _save(game, state)
                    socketio.emit("game_state", serialize(game), room=f"game:{game_id}", namespace="/game")
                    continue

                game.status = "finished" if state["result"] is not None else game.status
                _save(game, state)
                socketio.emit("game_state", serialize(game), room=f"game:{game_id}", namespace="/game")
                if state["result"] is not None:
                    _record_results(game, state)
                    return
                if state["turn"] != 1:
                    return
        finally:
            rt["bot_running"] = False


def schedule_disconnect_grace(game_id, user_id, is_still_connected):
    socketio.start_background_task(_disconnect_grace, game_id, user_id, is_still_connected)


def _disconnect_grace(game_id, user_id, is_still_connected):
    with _app_context():
        socketio.sleep(DISCONNECT_GRACE_SECONDS)
        if is_still_connected():
            return
        game = db.session.get(Game, game_id)
        if game is None or game.status != "active":
            return
        idx = _player_index(game, user_id)
        if idx is None:
            return
        state = dict(game.state_json)
        result_state = _finalize_resign(game, state, resigned_by=idx)
        socketio.emit("game_state", result_state, room=f"game:{game_id}", namespace="/game")
