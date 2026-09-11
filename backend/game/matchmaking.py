_queue = []


def join_queue(user_id, sid):
    if any(u == user_id for u, _ in _queue):
        return None
    if _queue:
        return _queue.pop(0)
    _queue.append((user_id, sid))
    return None


def leave_queue(user_id, sid=None):
    # With a sid, only that one connection's entry is dropped -- a user with
    # a second tab open should stay queued when the other tab closes. Without
    # one (an explicit "cancel"), every entry for the user goes.
    global _queue
    _queue = [(u, s) for u, s in _queue if u != user_id or (sid is not None and s != sid)]


def clear():
    global _queue
    _queue = []
