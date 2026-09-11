import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from config import TestConfig  # noqa: E402
from extensions import db as _db  # noqa: E402


@pytest.fixture(autouse=True)
def reset_process_state():
    """Drop the module-level maps that outlive a single test.

    Socket presence and the manager's per-game runtime flags live in plain
    module dicts, and every test starts from an empty database where game
    ids begin at 1 again -- so leftovers from an earlier test would collide
    with a fresh game of the same id.
    """
    from game import manager as _manager, socket_handlers as _handlers

    def _clear():
        _handlers._sid_user.clear()
        _handlers._user_sids.clear()
        _manager._runtime.clear()

    _clear()
    yield
    _clear()


@pytest.fixture
def app():
    application = create_app(TestConfig)
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def client(app):
    return app.test_client()


from werkzeug.security import generate_password_hash  # noqa: E402
from models import User  # noqa: E402


@pytest.fixture
def make_user(db):
    def _make(email="a@example.com", password="secret123", display_name="Alice"):
        user = User(email=email, password_hash=generate_password_hash(password), display_name=display_name)
        db.session.add(user)
        db.session.commit()
        return user
    return _make
