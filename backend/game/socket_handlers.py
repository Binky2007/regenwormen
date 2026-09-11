from flask import request
from flask_jwt_extended import decode_token
from flask_socketio import join_room, emit, ConnectionRefusedError
from game import manager, matchmaking

# Presence is tracked per *connection*, not per user: `_sid_user` maps a
# socket id to its user, and `_user_sids` maps a user to every socket they
# currently have open. A user counts as connected until their last socket
# goes away -- otherwise closing a second tab (say, the leaderboard) would
# look like a disconnect and auto-resign the live game in the first tab.
_sid_user = {}
_user_sids = {}


def _track_connection(sid, user_id):
    _sid_user[sid] = user_id
    _user_sids.setdefault(user_id, set()).add(sid)


def _untrack_connection(sid):
    user_id = _sid_user.pop(sid, None)
    if user_id is None:
        return None
    sids = _user_sids.get(user_id)
    if sids is not None:
        sids.discard(sid)
        if not sids:
            del _user_sids[user_id]
    return user_id


def is_user_connected(user_id):
    return bool(_user_sids.get(user_id))


def register_handlers(socketio_instance):
    @socketio_instance.on("connect", namespace="/game")
    def on_connect(auth):
        token = (auth or {}).get("token")
        if not token:
            raise ConnectionRefusedError("missing token")
        try:
            decoded = decode_token(token)
        except Exception:
            raise ConnectionRefusedError("invalid token")
        user_id = int(decoded["sub"])
        _track_connection(request.sid, user_id)

    @socketio_instance.on("resume_game", namespace="/game")
    def on_resume_game():
        # A client that just (re)connected -- a page refresh, a dropped
        # network, or a backend restart -- asks the server which game it is
        # in. The server owns that answer, so the client sends no game id.
        user_id = _sid_user.get(request.sid)
        if user_id is None:
            return
        state = manager.resume_active_game(user_id)
        if state is None:
            return
        join_room(f"game:{state['game_id']}")
        emit("game_state", state)

    @socketio_instance.on("start_bot_game", namespace="/game")
    def on_start_bot_game():
        user_id = _sid_user.get(request.sid)
        if user_id is None:
            return
        game = manager.create_bot_game(user_id)
        join_room(f"game:{game.id}")
        emit("game_state", manager.serialize(game))

    @socketio_instance.on("action", namespace="/game")
    def on_action(data):
        user_id = _sid_user.get(request.sid)
        if user_id is None:
            return
        game_id = data.get("game_id")
        state, error = manager.apply_action(game_id, user_id, data.get("type"), data.get("payload"))
        if error:
            emit("error", {"message": error})
        else:
            emit("game_state", state, room=f"game:{game_id}")

    @socketio_instance.on("find_match", namespace="/game")
    def on_find_match():
        user_id = _sid_user.get(request.sid)
        if user_id is None:
            return
        match = matchmaking.join_queue(user_id, request.sid)
        if match is None:
            return
        other_user_id, other_sid = match
        game = manager.create_pvp_game(other_user_id, user_id)
        room = f"game:{game.id}"
        join_room(room)
        socketio_instance.server.enter_room(other_sid, room, namespace="/game")
        emit("match_found", {"game_id": game.id}, room=room)
        emit("game_state", manager.serialize(game), room=room)

    @socketio_instance.on("cancel_match", namespace="/game")
    def on_cancel_match():
        user_id = _sid_user.get(request.sid)
        if user_id is not None:
            matchmaking.leave_queue(user_id)

    @socketio_instance.on("disconnect", namespace="/game")
    def on_disconnect():
        sid = request.sid
        user_id = _untrack_connection(sid)
        if user_id is None:
            return
        # Only this connection's queue entry goes: another tab of the same
        # user may still be legitimately waiting for an opponent.
        matchmaking.leave_queue(user_id, sid=sid)
        if is_user_connected(user_id):
            return
        for game_id in manager.active_pvp_game_ids_for_user(user_id):
            manager.schedule_disconnect_grace(
                game_id, user_id, lambda uid=user_id: is_user_connected(uid)
            )
