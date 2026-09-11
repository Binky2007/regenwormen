from game.engine import selectable, val


def bot_value(state, face):
    count = state["roll"].count(face)
    bonus = 8 if face == "w" and "w" not in state["aside"] else 0
    return count * val(face) + bonus


def choose_bot_face(state):
    sel = selectable(state)
    if not sel:
        return None
    return max(sel, key=lambda f: bot_value(state, f))
