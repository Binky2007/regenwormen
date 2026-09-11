import random

FACES = [1, 2, 3, 4, 5, "w"]


def worms_on(n):
    if n <= 24:
        return 1
    if n <= 28:
        return 2
    if n <= 32:
        return 3
    return 4


def val(face):
    return 5 if face == "w" else face


def fresh_game():
    return {
        "center": list(range(21, 37)),
        "out": [],
        "stacks": [[], []],
        "turn": 0,
        "roll": [],
        "aside": [],
        "best_scores": [0, 0],
        "log": [],
        "result": None,
    }


def score(aside):
    return sum(val(f) for f in aside)


def selectable(state):
    used = set(state["aside"])
    out = []
    for f in state["roll"]:
        if f not in used and f not in out:
            out.append(f)
    return out


def options(state, sc):
    if sc < 21 or "w" not in state["aside"]:
        return []
    result = []
    other = state["stacks"][1 - state["turn"]]
    top = other[-1] if other else None
    if top == sc:
        result.append({"kind": "steal", "num": sc})
    takeable = [n for n in state["center"] if n <= sc]
    if takeable:
        result.append({"kind": "take", "num": max(takeable)})
    return result


def _push_log(state, text):
    state["log"] = ([{"text": text}] + state["log"])[:40]


def roll_into(state):
    n = 8 - len(state["aside"])
    state["roll"] = [random.choice(FACES) for _ in range(n)]
    return state


def pick_into(state, face, actor_name):
    kept = [f for f in state["roll"] if f == face]
    state["aside"] = state["aside"] + kept
    state["roll"] = []
    label = "worm" if face == "w" else str(face)
    _push_log(state, f"{actor_name} set aside {len(kept)}× {label} for {score(state['aside'])} pts")
    return state


def bust_into(state, actor_name, reason=None):
    idx = state["turn"]
    stack = list(state["stacks"][idx])
    note = f"{actor_name} busted" + (f" ({reason})" if reason else "")
    if stack:
        back = stack.pop()
        state["stacks"][idx] = stack
        center = sorted(state["center"] + [back])
        highest = center[-1]
        if highest != back:
            state["center"] = [n for n in center if n != highest]
            state["out"] = state["out"] + [highest]
            note += f". Tile {back} returned, {highest} out of play"
        else:
            state["center"] = center
            note += f". Tile {back} returned"
    else:
        note += ", no tile to lose"
    _push_log(state, note)
    return end_turn(state)


def claim_into(state, opt, actor_name):
    idx = state["turn"]
    sc = score(state["aside"])
    state["best_scores"][idx] = max(state["best_scores"][idx], sc)
    if opt["kind"] == "steal":
        other_idx = 1 - idx
        other = list(state["stacks"][other_idx])
        other.pop()
        state["stacks"][other_idx] = other
        state["stacks"][idx] = state["stacks"][idx] + [opt["num"]]
        _push_log(state, f"{actor_name} stole tile {opt['num']}!")
    else:
        state["center"] = [n for n in state["center"] if n != opt["num"]]
        state["stacks"][idx] = state["stacks"][idx] + [opt["num"]]
        _push_log(state, f"{actor_name} took tile {opt['num']}")
    return end_turn(state)


def end_turn(state):
    state["roll"] = []
    state["aside"] = []
    if not state["center"]:
        worms = [sum(worms_on(n) for n in s) for s in state["stacks"]]
        winner = None if worms[0] == worms[1] else (0 if worms[0] > worms[1] else 1)
        state["result"] = {"winner": winner, "worms": worms}
        return state
    state["turn"] = 1 - state["turn"]
    return state
