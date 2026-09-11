import pytest
from game import matchmaking


@pytest.fixture(autouse=True)
def _reset():
    matchmaking.clear()
    yield
    matchmaking.clear()


def test_join_queue_pairs_second_caller_with_first():
    assert matchmaking.join_queue(1, "sid-1") is None
    match = matchmaking.join_queue(2, "sid-2")
    assert match == (1, "sid-1")


def test_leave_queue_removes_waiting_user():
    matchmaking.join_queue(3, "sid-3")
    matchmaking.leave_queue(3)
    assert matchmaking.join_queue(4, "sid-4") is None


def test_join_queue_ignores_duplicate_join():
    matchmaking.join_queue(5, "sid-5")
    assert matchmaking.join_queue(5, "sid-5-new") is None
