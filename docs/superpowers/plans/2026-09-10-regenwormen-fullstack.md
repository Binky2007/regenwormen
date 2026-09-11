# Regenwormen Full-Stack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Regenwormen prototype (`docs/superpowers/specs/2026-09-09-regenwormen-fullstack-design.md`) as a real full-stack app: React frontend, Flask backend, MySQL persistence, real email/password auth, a server-authoritative game engine shared by bot games and live PvP, real-time matchmaking over Socket.IO, and a dev-friendly Docker Compose environment.

**Architecture:** Flask app factory backend (SQLAlchemy + MySQL, JWT auth, Flask-SocketIO `/game` namespace) owns all game logic; React (Vite) is a pure view layer that renders whatever state the server emits and dispatches action events. Bot games and PvP games share one code path through a single Python game engine module.

**Tech Stack:** Python 3.12 / Flask 3 / Flask-SQLAlchemy / Flask-JWT-Extended / Flask-SocketIO (threading async mode) / PyMySQL / MySQL 8 / pytest — React 18 / Vite / react-router-dom / socket.io-client — Docker Compose.

**Spec:** `docs/superpowers/specs/2026-09-09-regenwormen-fullstack-design.md`

## Global Constraints

- MySQL 8 via the PyMySQL driver (`mysql+pymysql://`), schema loaded from `mysql/init/001_schema.sql` on first container boot.
- Passwords hashed with `werkzeug.security`; auth tokens are JWTs from `flask-jwt-extended`, sent as `Authorization: Bearer` on REST calls and as `{token}` on the Socket.IO `connect` handshake.
- One Socket.IO namespace (`/game`) is shared by bot games and PvP games — the frontend never computes game logic, only renders `game_state` and emits `action` events.
- Flask-SocketIO runs with `async_mode="threading"` (not eventlet) so the Werkzeug debug reloader works reliably in the dev Docker setup.
- Docker Compose is dev-friendly only (hot reload both sides) — no production build/nginx/gunicorn in this pass.
- No frontend unit test suite is added; frontend tasks are verified via `curl` smoke checks (static/skeleton behavior) and precise manual browser steps (interactive/stateful behavior), per the spec.
- PvP disconnect handling: 30-second grace period, then auto-resign for the disconnected player. No reconnect-and-resume beyond that window.
- The hero image asset is already saved at `frontend/public/regenwormen-tiles.png` (pulled from the source Claude Design project) — reference it directly, do not re-fetch it.

---

## Task 1: MySQL schema + Docker Compose skeleton (database only)

**Files:**
- Create: `mysql/init/001_schema.sql`
- Create: `.env.example`
- Create: `.env` (copy of `.env.example` with dev values — not committed)
- Create: `.gitignore`
- Create: `docker-compose.yml` (mysql service only for now)

**Interfaces:**
- Produces: the `users`, `games`, `game_results` tables that every later backend task reads/writes.

- [ ] **Step 1: Write the schema**

```sql
-- mysql/init/001_schema.sql
CREATE TABLE users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  email         VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  display_name  VARCHAR(64)  NOT NULL,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE games (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  mode          ENUM('bot','pvp') NOT NULL,
  player1_id    INT NOT NULL,
  player2_id    INT NULL,
  status        ENUM('active','finished','resigned') NOT NULL DEFAULT 'active',
  state_json    JSON NOT NULL,
  winner        ENUM('player1','player2','draw') NULL,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at   DATETIME NULL,
  FOREIGN KEY (player1_id) REFERENCES users(id),
  FOREIGN KEY (player2_id) REFERENCES users(id)
);

CREATE TABLE game_results (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  game_id         INT NOT NULL,
  user_id         INT NOT NULL,
  worms           INT NOT NULL,
  tiles_won       JSON NOT NULL,
  is_winner       BOOLEAN NOT NULL,
  best_turn_score INT NOT NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (game_id) REFERENCES games(id),
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

- [ ] **Step 2: Write `.env.example` and copy it to `.env`**

```
MYSQL_ROOT_PASSWORD=change-me-root
MYSQL_DATABASE=regenwormen
MYSQL_USER=regenwormen
MYSQL_PASSWORD=change-me
JWT_SECRET_KEY=change-me-too
```

Run: `cp .env.example .env`

- [ ] **Step 3: Write `.gitignore`**

```
.env
node_modules/
__pycache__/
*.pyc
frontend/dist/
```

- [ ] **Step 4: Write the Compose skeleton (mysql only)**

```yaml
# docker-compose.yml
services:
  mysql:
    image: mysql:8
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DATABASE}
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./mysql/init:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p${MYSQL_ROOT_PASSWORD}"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  mysql_data:
```

- [ ] **Step 5: Verify the schema loads**

Run: `docker compose up -d mysql && sleep 20 && docker compose exec mysql mysql -u$MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DATABASE -e "SHOW TABLES;"`
Expected: lists `users`, `games`, `game_results`.

Run: `docker compose down -v` (tear down before the next task changes the compose file)

- [ ] **Step 6: Commit**

```bash
git add mysql .env.example .gitignore docker-compose.yml
git commit -m "feat: add MySQL schema and Docker Compose skeleton"
```

---

## Task 2: Backend Flask skeleton (app factory, config, health check)

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/config.py`
- Create: `backend/extensions.py`
- Create: `backend/app.py`
- Create: `backend/Dockerfile`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`
- Modify: `docker-compose.yml` (add `backend` service)

**Interfaces:**
- Consumes: `mysql` service from Task 1 (env vars `MYSQL_HOST`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`).
- Produces: `create_app(config_object=Config)` — the app factory every later backend task imports; `db`, `jwt`, `socketio` singletons from `extensions.py`.

- [ ] **Step 1: Write requirements**

```
# backend/requirements.txt
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
Flask-JWT-Extended==4.6.0
Flask-SocketIO==5.3.6
Flask-Cors==4.0.1
PyMySQL==1.1.1
python-socketio==5.11.2
pytest==8.2.0
```

- [ ] **Step 2: Write config**

```python
# backend/config.py
import os


class Config:
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{os.environ.get('MYSQL_USER', 'regenwormen')}:"
        f"{os.environ.get('MYSQL_PASSWORD', 'regenwormen')}@"
        f"{os.environ.get('MYSQL_HOST', 'mysql')}:3306/"
        f"{os.environ.get('MYSQL_DATABASE', 'regenwormen')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 12


class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    TESTING = True
    JWT_SECRET_KEY = "test-secret"
```

- [ ] **Step 3: Write extensions**

```python
# backend/extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO

db = SQLAlchemy()
jwt = JWTManager()
socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")
```

- [ ] **Step 4: Write the app factory with a health endpoint**

```python
# backend/app.py
from flask import Flask
from flask_cors import CORS
from config import Config
from extensions import db, jwt, socketio


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)
    jwt.init_app(app)
    socketio.init_app(app)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    app = create_app()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
```

- [ ] **Step 5: Write test fixtures**

```python
# backend/tests/conftest.py
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from config import TestConfig  # noqa: E402
from extensions import db as _db  # noqa: E402


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
```

- [ ] **Step 6: Write the failing test**

```python
# backend/tests/test_health.py
def test_health_returns_ok(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.get_json() == {"status": "ok"}
```

- [ ] **Step 7: Run test to verify it fails**

Run: `cd backend && pip install -r requirements.txt && python -m pytest tests/test_health.py -v`
Expected: FAIL (no app/module yet, or import error) — this confirms the test harness is wired before the app exists in a runnable state. If Steps 1-4 are already done, this should actually PASS; if so skip to Step 8 (this task's implementation is small enough that test-first and implementation land together).

- [ ] **Step 8: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 9: Write the Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

- [ ] **Step 10: Wire the backend service into Compose**

```yaml
# docker-compose.yml — add under services, after mysql:
  backend:
    build: ./backend
    restart: unless-stopped
    environment:
      MYSQL_HOST: mysql
      MYSQL_DATABASE: ${MYSQL_DATABASE}
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
    ports:
      - "5000:5000"
    volumes:
      - ./backend:/app
    depends_on:
      mysql:
        condition: service_healthy
```

- [ ] **Step 11: Verify end-to-end against real MySQL**

Run: `docker compose up -d --build mysql backend && sleep 15 && curl -s http://localhost:5000/api/health`
Expected: `{"status":"ok"}`

Run: `docker compose down`

- [ ] **Step 12: Commit**

```bash
git add backend docker-compose.yml
git commit -m "feat: add Flask app factory and backend Docker service"
```

---

## Task 3: Frontend Vite skeleton + Docker service

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.jsx`
- Create: `frontend/src/App.jsx` (placeholder — replaced in Task 13)
- Create: `frontend/Dockerfile`
- Modify: `docker-compose.yml` (add `frontend` service)

**Interfaces:**
- Consumes: `backend` service health endpoint (Task 2) via the dev-server proxy.
- Produces: a running Vite dev container other frontend tasks build on top of.

- [ ] **Step 1: Write package.json**

```json
{
  "name": "regenwormen-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.24.0",
    "socket.io-client": "^4.7.5"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.1",
    "vite": "^5.3.0"
  }
}
```

- [ ] **Step 2: Write the Vite config with a dev proxy to the backend**

```js
// frontend/vite.config.js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': { target: 'http://backend:5000', changeOrigin: true },
      '/socket.io': { target: 'http://backend:5000', ws: true, changeOrigin: true },
    },
  },
})
```

- [ ] **Step 3: Write index.html**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Archivo:ital,wght@0,400;0,600;0,700;0,900;1,400&display=swap" rel="stylesheet" />
    <title>Regenwormen</title>
    <style>
      html, body { margin: 0; padding: 0; background: #e9e3d5; }
      * { box-sizing: border-box; }
      a { color: #a8232b; }
      @keyframes rw-spin { to { transform: rotate(360deg) } }
    </style>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 4: Write main.jsx and a placeholder App.jsx**

```jsx
// frontend/src/main.jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```

```jsx
// frontend/src/App.jsx
export default function App() {
  return <div style={{ padding: 40, fontFamily: 'sans-serif' }}>Regenwormen — frontend booting.</div>
}
```

- [ ] **Step 5: Write the Dockerfile**

```dockerfile
# frontend/Dockerfile
FROM node:20-slim
WORKDIR /app
COPY package.json package-lock.json* .
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]
```

- [ ] **Step 6: Wire the frontend service into Compose**

```yaml
# docker-compose.yml — add under services, after backend:
  frontend:
    build: ./frontend
    restart: unless-stopped
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - backend
```

- [ ] **Step 7: Verify the full stack boots end-to-end**

Run: `docker compose up -d --build && sleep 20 && curl -s http://localhost:5173/ | grep -o '<title>[^<]*</title>'`
Expected: `<title>Regenwormen</title>`

Run: `curl -s http://localhost:5173/api/health`
Expected: `{"status":"ok"}` (proves the Vite dev-server proxy reaches the backend container)

Run: `docker compose down`

- [ ] **Step 8: Commit**

```bash
git add frontend docker-compose.yml
git commit -m "feat: add Vite frontend skeleton and Docker service"
```

---

## Task 4: SQLAlchemy models

**Files:**
- Create: `backend/models.py`
- Create: `backend/tests/test_models.py`

**Interfaces:**
- Consumes: `db` from `extensions.py` (Task 2).
- Produces: `User`, `Game`, `GameResult` models — used by every later backend task.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_models.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'models'`

- [ ] **Step 3: Write the models**

```python
# backend/models.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Add a reusable `make_user` fixture for later tasks**

```python
# backend/tests/conftest.py — append:
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
```

- [ ] **Step 6: Commit**

```bash
git add backend/models.py backend/tests/test_models.py backend/tests/conftest.py
git commit -m "feat: add User, Game and GameResult models"
```

---

## Task 5: Auth routes (signup / login / me)

**Files:**
- Create: `backend/auth/__init__.py`
- Create: `backend/auth/routes.py`
- Create: `backend/tests/test_auth.py`
- Modify: `backend/app.py` (register the auth blueprint)

**Interfaces:**
- Consumes: `User` model (Task 4).
- Produces: `POST /api/auth/signup`, `POST /api/auth/login`, `GET /api/auth/me` — used by the frontend `AuthContext` (Task 13) and by JWTs the Socket.IO handshake (Task 9) validates.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_auth.py
def test_signup_creates_user_and_returns_token(client):
    res = client.post("/api/auth/signup", json={
        "email": "carlos@example.com", "password": "hunter22", "display_name": "Carlos",
    })
    assert res.status_code == 201
    body = res.get_json()
    assert body["user"]["email"] == "carlos@example.com"
    assert "token" in body


def test_signup_rejects_duplicate_email(client, make_user):
    make_user(email="dup@example.com")
    res = client.post("/api/auth/signup", json={
        "email": "dup@example.com", "password": "hunter22", "display_name": "Someone",
    })
    assert res.status_code == 409


def test_login_with_correct_password_returns_token(client, make_user):
    make_user(email="login@example.com", password="correct-horse")
    res = client.post("/api/auth/login", json={"email": "login@example.com", "password": "correct-horse"})
    assert res.status_code == 200
    assert "token" in res.get_json()


def test_login_with_wrong_password_is_rejected(client, make_user):
    make_user(email="login2@example.com", password="correct-horse")
    res = client.post("/api/auth/login", json={"email": "login2@example.com", "password": "wrong"})
    assert res.status_code == 401


def test_me_requires_auth(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_me_returns_current_user(client, make_user):
    make_user(email="me@example.com", password="hunter22", display_name="Me")
    login = client.post("/api/auth/login", json={"email": "me@example.com", "password": "hunter22"})
    token = login.get_json()["token"]
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.get_json()["display_name"] == "Me"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: FAIL (404s — no blueprint registered yet)

- [ ] **Step 3: Write the auth blueprint**

```python
# backend/auth/__init__.py
```

```python
# backend/auth/routes.py
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from extensions import db
from models import User

auth_bp = Blueprint("auth", __name__)


def _user_dict(user):
    return {"id": user.id, "email": user.email, "display_name": user.display_name}


@auth_bp.post("/signup")
def signup():
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    display_name = (data.get("display_name") or "").strip()
    if not email or not password or not display_name:
        return jsonify({"error": "email, password and display_name are required"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "an account with that email already exists"}), 409
    user = User(email=email, password_hash=generate_password_hash(password), display_name=display_name)
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=str(user.id))
    return jsonify({"token": token, "user": _user_dict(user)}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "invalid email or password"}), 401
    token = create_access_token(identity=str(user.id))
    return jsonify({"token": token, "user": _user_dict(user)}), 200


@auth_bp.get("/me")
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(_user_dict(user))
```

- [ ] **Step 4: Register the blueprint in the app factory**

```python
# backend/app.py — inside create_app(), after socketio.init_app(app):
    from auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: PASS (6 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/auth backend/tests/test_auth.py backend/app.py
git commit -m "feat: add signup/login/me auth endpoints"
```

---

## Task 6: Game engine (pure Python port)

**Files:**
- Create: `backend/game/__init__.py`
- Create: `backend/game/engine.py`
- Create: `backend/tests/test_engine.py`

**Interfaces:**
- Produces: `fresh_game()`, `score(aside)`, `selectable(state)`, `options(state, sc)`, `roll_into(state)`, `pick_into(state, face, actor_name)`, `bust_into(state, actor_name, reason=None)`, `claim_into(state, opt, actor_name)`, `end_turn(state)`, `worms_on(n)`, `val(face)` — the single source of game-rule truth used by `game/manager.py` (Task 8) and `game/bot.py` (Task 7). State shape: `{center, out, stacks: [[],[]], turn, roll, aside, best_scores: [0,0], log, result}`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_engine.py
from game.engine import (
    fresh_game, score, selectable, options, roll_into, pick_into,
    bust_into, claim_into, end_turn, worms_on, val,
)


def test_worms_on_boundaries():
    assert worms_on(21) == 1
    assert worms_on(24) == 1
    assert worms_on(25) == 2
    assert worms_on(28) == 2
    assert worms_on(29) == 3
    assert worms_on(32) == 3
    assert worms_on(33) == 4
    assert worms_on(36) == 4


def test_val():
    assert val(3) == 3
    assert val("w") == 5


def test_score_sums_worms_as_five():
    assert score([3, 3, "w", "w"]) == 16


def test_selectable_excludes_already_used_faces():
    state = fresh_game()
    state["roll"] = [3, 3, 5, "w"]
    state["aside"] = [5, 5]
    assert selectable(state) == [3, "w"]


def test_options_requires_worm_and_min_21():
    state = fresh_game()
    state["aside"] = [4, 4, 4]
    assert options(state, score(state["aside"])) == []
    state["aside"] = [5, 5, 5, 5, "w"]
    sc = score(state["aside"])
    assert sc == 25
    assert options(state, sc) == [{"kind": "take", "num": 25}]


def test_options_offers_steal_when_top_tile_matches():
    state = fresh_game()
    state["aside"] = ["w", "w", "w", "w", "w", 5]
    sc = score(state["aside"])
    assert sc == 30
    state["stacks"][1] = [30]
    opts = options(state, sc)
    assert {"kind": "steal", "num": 30} in opts


def test_roll_into_fills_remaining_dice():
    state = fresh_game()
    state["aside"] = [5, 5]
    state = roll_into(state)
    assert len(state["roll"]) == 6
    assert all(f in (1, 2, 3, 4, 5, "w") for f in state["roll"])


def test_pick_into_moves_matching_dice_to_aside_and_logs():
    state = fresh_game()
    state["roll"] = [4, 4, 3, "w"]
    state = pick_into(state, 4, "Alice")
    assert state["aside"] == [4, 4]
    assert state["roll"] == []
    assert "Alice set aside 2" in state["log"][0]["text"]


def test_bust_into_returns_top_tile_and_ends_turn():
    state = fresh_game()
    state["stacks"][0] = [24, 30]
    state = bust_into(state, "Alice", "no new value")
    assert 30 in state["center"]
    assert state["stacks"][0] == [24]
    assert state["turn"] == 1
    assert "busted" in state["log"][0]["text"]


def test_bust_into_with_no_tiles_just_ends_turn():
    state = fresh_game()
    state = bust_into(state, "Alice")
    assert state["turn"] == 1
    assert state["stacks"][0] == []


def test_claim_into_take_removes_tile_from_center_and_tracks_best_score():
    state = fresh_game()
    state["aside"] = [5, 5, 5, 5, "w"]
    state = claim_into(state, {"kind": "take", "num": 25}, "Alice")
    assert 25 not in state["center"]
    assert state["stacks"][0] == [25]
    assert state["best_scores"][0] == 25
    assert state["turn"] == 1


def test_claim_into_steal_moves_tile_between_stacks():
    state = fresh_game()
    state["stacks"][1] = [22, 28]
    state["aside"] = [5, 5, 5, 5, "w"]
    state = claim_into(state, {"kind": "steal", "num": 28}, "Alice")
    assert state["stacks"][1] == [22]
    assert state["stacks"][0] == [28]


def test_end_turn_finishes_game_when_center_empty():
    state = fresh_game()
    state["center"] = []
    state["stacks"] = [[21, 25], [36]]
    state = end_turn(state)
    assert state["result"]["winner"] == 1
    assert state["result"]["worms"] == [3, 4]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'game'`

- [ ] **Step 3: Write the engine**

```python
# backend/game/__init__.py
```

```python
# backend/game/engine.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_engine.py -v`
Expected: PASS (13 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/game backend/tests/test_engine.py
git commit -m "feat: add pure Python game engine"
```

---

## Task 7: Bot move heuristic

**Files:**
- Create: `backend/game/bot.py`
- Create: `backend/tests/test_bot.py`

**Interfaces:**
- Consumes: `selectable(state)`, `val(face)` from `game/engine.py` (Task 6).
- Produces: `bot_value(state, face)`, `choose_bot_face(state)` — used by `game/manager.py` (Task 8) to drive bot turns.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_bot.py
from game.engine import fresh_game
from game.bot import bot_value, choose_bot_face


def test_bot_value_prefers_worms_with_bonus():
    state = fresh_game()
    state["roll"] = ["w", "w", 5, 5, 5]
    assert bot_value(state, "w") == 2 * 5 + 8
    assert bot_value(state, 5) == 15


def test_choose_bot_face_picks_highest_value():
    state = fresh_game()
    state["roll"] = [1, 1, "w"]
    assert choose_bot_face(state) == "w"


def test_choose_bot_face_returns_none_when_nothing_selectable():
    state = fresh_game()
    state["roll"] = [3, 3]
    state["aside"] = [3, 3, 3]
    assert choose_bot_face(state) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_bot.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'game.bot'`

- [ ] **Step 3: Write the bot heuristic**

```python
# backend/game/bot.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_bot.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/game/bot.py backend/tests/test_bot.py
git commit -m "feat: add bot move heuristic"
```

---

## Task 8: GameManager (create, apply_action, persist, finalize)

**Files:**
- Create: `backend/game/manager.py`
- Create: `backend/tests/test_game_manager.py`
- Modify: `backend/app.py` (call `manager.init_app(app)`)

**Interfaces:**
- Consumes: `Game`, `GameResult`, `User` models (Task 4); `fresh_game`, `roll_into`, `pick_into`, `bust_into`, `claim_into`, `selectable`, `options`, `score`, `worms_on` (Task 6); `choose_bot_face` (Task 7); `db`, `socketio` (Task 2).
- Produces: `init_app(app)`, `create_bot_game(user_id) -> Game`, `create_pvp_game(user1_id, user2_id) -> Game`, `serialize(game) -> dict`, `apply_action(game_id, user_id, action_type, payload=None) -> (state_dict_or_None, error_or_None)`, `active_pvp_game_ids_for_user(user_id) -> list[int]`, `schedule_disconnect_grace(game_id, user_id, is_still_connected)`. Consumed by `game/socket_handlers.py` (Task 9) and `game/matchmaking.py`-driven flows (Task 11/12).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_game_manager.py
import pytest
from game import engine, manager
from models import Game


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(manager.socketio, "sleep", lambda s: None)


def test_create_bot_game_persists_fresh_state(app, make_user):
    user = make_user()
    game = manager.create_bot_game(user.id)
    assert game.mode == "bot"
    assert game.status == "active"
    assert game.state_json["center"] == list(range(21, 37))


def test_apply_action_rejects_non_player(app, make_user):
    user = make_user()
    game = manager.create_bot_game(user.id)
    state, error = manager.apply_action(game.id, 999999, "roll")
    assert state is None
    assert "not a player" in error


def test_full_human_turn_claims_a_tile(app, make_user, monkeypatch):
    seq = iter([5, 5, 5, 5, "w", "w", 1, 2, "w", "w", 3, 4])
    monkeypatch.setattr(engine.random, "choice", lambda faces: next(seq))

    user = make_user()
    game = manager.create_bot_game(user.id)

    state, error = manager.apply_action(game.id, user.id, "roll")
    assert error is None
    assert state["roll"] == [5, 5, 5, 5, "w", "w", 1, 2]

    state, error = manager.apply_action(game.id, user.id, "pick", {"face": 5})
    assert error is None
    assert state["aside"] == [5, 5, 5, 5]

    state, error = manager.apply_action(game.id, user.id, "roll")
    assert error is None
    assert state["roll"] == ["w", "w", 3, 4]

    state, error = manager.apply_action(game.id, user.id, "pick", {"face": "w"})
    assert error is None
    assert state["aside"] == [5, 5, 5, 5, "w", "w"]

    state, error = manager.apply_action(game.id, user.id, "claim", {"kind": "take", "num": 30})
    assert error is None
    assert state["stacks"][0] == [30]
    assert state["turn"] == 1
    assert state["player1_id"] == user.id


def test_resign_finalizes_game_as_a_loss(app, make_user):
    alice = make_user(email="a@example.com", display_name="Alice")
    bob = make_user(email="b@example.com", display_name="Bob")
    game = manager.create_pvp_game(alice.id, bob.id)

    state, error = manager.apply_action(game.id, alice.id, "resign")
    assert error is None
    assert state["result"]["winner"] == 1
    assert state["status"] == "resigned"


def test_bot_turn_runs_to_completion_and_claims_a_tile(app, make_user, monkeypatch, db):
    seq = iter([5, 5, 5, 5, 5, 5, 5, "w", "w"])
    monkeypatch.setattr(engine.random, "choice", lambda faces: next(seq))

    user = make_user()
    game = manager.create_bot_game(user.id)
    game.state_json = {**game.state_json, "turn": 1}
    db.session.add(game)
    db.session.commit()

    manager._run_bot_turn(game.id, speed=0)

    refreshed = db.session.get(Game, game.id)
    assert 36 in refreshed.state_json["stacks"][1]
    assert refreshed.state_json["turn"] == 0
```

Note: `test_full_human_turn_claims_a_tile` expects `state["player1_id"]` in the returned dict — that's from `serialize()`, confirming `apply_action` returns the full serialized payload, not just the raw engine state.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_game_manager.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'game.manager'`

- [ ] **Step 3: Write the manager**

```python
# backend/game/manager.py
from datetime import datetime
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


def _schedule_bot_turn(game_id):
    rt = _runtime_for(game_id)
    if rt["bot_running"]:
        return
    rt["bot_running"] = True
    socketio.start_background_task(_run_bot_turn, game_id)


def _run_bot_turn(game_id, speed=0.7):
    rt = _runtime_for(game_id)
    with _app.app_context():
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
    with _app.app_context():
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
```

- [ ] **Step 4: Wire `init_app` into the app factory**

```python
# backend/app.py — inside create_app(), after registering auth_bp:
    from game import manager
    manager.init_app(app)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_game_manager.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Run the full backend suite to check nothing broke**

Run: `cd backend && python -m pytest -v`
Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/game/manager.py backend/tests/test_game_manager.py backend/app.py
git commit -m "feat: add GameManager for bot/pvp game lifecycle and persistence"
```

---

## Task 9: Socket.IO handlers for bot gameplay

**Files:**
- Create: `backend/game/socket_handlers.py`
- Create: `backend/tests/test_socket_bot.py`
- Modify: `backend/app.py` (register handlers)

**Interfaces:**
- Consumes: `manager.create_bot_game`, `manager.apply_action`, `manager.serialize` (Task 8).
- Produces: `register_handlers(socketio_instance)` — wires the `/game` namespace events `connect`, `start_bot_game`, `action`, `disconnect`. Consumed by `app.py`; extended by Task 11 (`find_match`/`cancel_match`) and Task 12 (disconnect grace).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_socket_bot.py
from flask_jwt_extended import create_access_token
from extensions import socketio


def _token_for(app, user):
    with app.app_context():
        return create_access_token(identity=str(user.id))


def test_connect_without_token_is_refused(app):
    client = socketio.test_client(app, namespace="/game")
    assert not client.is_connected(namespace="/game")


def test_start_bot_game_returns_initial_state(app, make_user, monkeypatch):
    from game import manager
    monkeypatch.setattr(manager.socketio, "sleep", lambda s: None)
    user = make_user()
    token = _token_for(app, user)
    client = socketio.test_client(app, namespace="/game", auth={"token": token})
    assert client.is_connected(namespace="/game")

    client.emit("start_bot_game", namespace="/game")
    received = client.get_received(namespace="/game")
    states = [m for m in received if m["name"] == "game_state"]
    assert states
    payload = states[0]["args"][0]
    assert payload["center"] == list(range(21, 37))
    assert payload["turn"] == 0


def test_action_rejects_illegal_move(app, make_user, monkeypatch):
    from game import manager
    monkeypatch.setattr(manager.socketio, "sleep", lambda s: None)
    user = make_user()
    token = _token_for(app, user)
    client = socketio.test_client(app, namespace="/game", auth={"token": token})
    client.emit("start_bot_game", namespace="/game")
    game_id = [m for m in client.get_received(namespace="/game") if m["name"] == "game_state"][0]["args"][0]["game_id"]

    client.emit("action", {"game_id": game_id, "type": "pick", "payload": {"face": 5}}, namespace="/game")
    received = client.get_received(namespace="/game")
    errors = [m for m in received if m["name"] == "error"]
    assert errors
    assert "not selectable" in errors[0]["args"][0]["message"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_socket_bot.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'game.socket_handlers'`

- [ ] **Step 3: Write the handlers**

```python
# backend/game/socket_handlers.py
from flask import request
from flask_jwt_extended import decode_token
from flask_socketio import join_room, emit
from game import manager

_sid_user = {}
_connected_users = set()


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
        _sid_user[request.sid] = user_id
        _connected_users.add(user_id)

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

    @socketio_instance.on("disconnect", namespace="/game")
    def on_disconnect():
        user_id = _sid_user.pop(request.sid, None)
        if user_id is None:
            return
        _connected_users.discard(user_id)
```

- [ ] **Step 4: Register the handlers in the app factory**

```python
# backend/app.py — inside create_app(), after manager.init_app(app):
    from game.socket_handlers import register_handlers
    register_handlers(socketio)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_socket_bot.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/game/socket_handlers.py backend/tests/test_socket_bot.py backend/app.py
git commit -m "feat: add Socket.IO handlers for authenticated bot gameplay"
```

---

## Task 10: Leaderboard & profile REST endpoints

**Files:**
- Create: `backend/stats/__init__.py`
- Create: `backend/stats/routes.py`
- Create: `backend/tests/test_stats.py`
- Modify: `backend/app.py` (register the stats blueprint)

**Interfaces:**
- Consumes: `User`, `GameResult` models (Task 4).
- Produces: `GET /api/leaderboard`, `GET /api/profile` — used by `Leaderboard.jsx`/`Profile.jsx` (Task 16).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_stats.py
from extensions import db
from models import Game, GameResult
from flask_jwt_extended import create_access_token


def _finish_game(winner, loser, worms_winner=10, worms_loser=4, best_turn=27):
    game = Game(mode="bot", player1_id=winner.id, player2_id=None, status="finished", state_json={})
    db.session.add(game)
    db.session.commit()
    db.session.add(GameResult(game_id=game.id, user_id=winner.id, worms=worms_winner, tiles_won=[30], is_winner=True, best_turn_score=best_turn))
    db.session.add(GameResult(game_id=game.id, user_id=loser.id, worms=worms_loser, tiles_won=[22], is_winner=False, best_turn_score=22))
    db.session.commit()


def test_leaderboard_orders_by_worms_desc(app, client, make_user):
    alice = make_user(email="a@example.com", display_name="Alice")
    bob = make_user(email="b@example.com", display_name="Bob")
    _finish_game(alice, bob)

    res = client.get("/api/leaderboard")
    assert res.status_code == 200
    names = [row["name"] for row in res.get_json()]
    assert names[0] == "Alice"


def test_profile_requires_auth(client):
    res = client.get("/api/profile")
    assert res.status_code == 401


def test_profile_returns_own_stats(app, client, make_user):
    alice = make_user(email="a@example.com", display_name="Alice")
    bob = make_user(email="b@example.com", display_name="Bob")
    _finish_game(alice, bob, worms_winner=15, best_turn=30)
    with app.app_context():
        token = create_access_token(identity=str(alice.id))

    res = client.get("/api/profile", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.get_json()
    assert body["worms"] == 15
    assert body["games"] == 1
    assert body["win_rate"] == 100
    assert body["best_turn"] == 30
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_stats.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'stats'`

- [ ] **Step 3: Write the stats blueprint**

```python
# backend/stats/__init__.py
```

```python
# backend/stats/routes.py
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
```

- [ ] **Step 4: Register the blueprint**

```python
# backend/app.py — inside create_app(), after auth_bp registration:
    from stats.routes import stats_bp
    app.register_blueprint(stats_bp, url_prefix="/api")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_stats.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/stats backend/tests/test_stats.py backend/app.py
git commit -m "feat: add leaderboard and profile endpoints"
```

---

## Task 11: Matchmaking + PvP game creation

**Files:**
- Create: `backend/game/matchmaking.py`
- Create: `backend/tests/test_matchmaking.py`
- Modify: `backend/game/socket_handlers.py` (add `find_match`/`cancel_match`)
- Modify: `backend/tests/test_socket_bot.py` → rename usage stays the same; add new PvP test file instead (see Step 5)

**Interfaces:**
- Produces: `join_queue(user_id, sid) -> (other_user_id, other_sid) | None`, `leave_queue(user_id)`, `clear()`.
- Consumes: `manager.create_pvp_game`, `manager.serialize` (Task 8) inside the `find_match` handler.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_matchmaking.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_matchmaking.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'game.matchmaking'`

- [ ] **Step 3: Write the matchmaking queue**

```python
# backend/game/matchmaking.py
_queue = []


def join_queue(user_id, sid):
    if any(u == user_id for u, _ in _queue):
        return None
    if _queue:
        return _queue.pop(0)
    _queue.append((user_id, sid))
    return None


def leave_queue(user_id):
    global _queue
    _queue = [(u, s) for u, s in _queue if u != user_id]


def clear():
    global _queue
    _queue = []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_matchmaking.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Add `find_match`/`cancel_match` handlers and a PvP socket test**

```python
# backend/game/socket_handlers.py — add imports and handlers:
from game import manager, matchmaking
```

```python
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
```

Also update `on_disconnect` to clear queue membership:

```python
    @socketio_instance.on("disconnect", namespace="/game")
    def on_disconnect():
        user_id = _sid_user.pop(request.sid, None)
        if user_id is None:
            return
        matchmaking.leave_queue(user_id)
        _connected_users.discard(user_id)
```

```python
# backend/tests/test_socket_pvp.py
from flask_jwt_extended import create_access_token
from extensions import socketio
from game import matchmaking


def _token_for(app, user):
    with app.app_context():
        return create_access_token(identity=str(user.id))


def test_find_match_pairs_two_waiting_players(app, make_user, monkeypatch):
    matchmaking.clear()
    from game import manager
    monkeypatch.setattr(manager.socketio, "sleep", lambda s: None)

    alice = make_user(email="a@example.com", display_name="Alice")
    bob = make_user(email="b@example.com", display_name="Bob")
    client_a = socketio.test_client(app, namespace="/game", auth={"token": _token_for(app, alice)})
    client_b = socketio.test_client(app, namespace="/game", auth={"token": _token_for(app, bob)})

    client_a.emit("find_match", namespace="/game")
    assert not any(m["name"] == "match_found" for m in client_a.get_received(namespace="/game"))

    client_b.emit("find_match", namespace="/game")
    received_b = client_b.get_received(namespace="/game")
    assert any(m["name"] == "match_found" for m in received_b)
    assert any(m["name"] == "game_state" for m in received_b)
```

- [ ] **Step 6: Run the new PvP test**

Run: `cd backend && python -m pytest tests/test_socket_pvp.py -v`
Expected: PASS

- [ ] **Step 7: Run the full backend suite**

Run: `cd backend && python -m pytest -v`
Expected: all tests PASS

- [ ] **Step 8: Commit**

```bash
git add backend/game/matchmaking.py backend/game/socket_handlers.py backend/tests/test_matchmaking.py backend/tests/test_socket_pvp.py
git commit -m "feat: add matchmaking queue and live PvP game creation"
```

---

## Task 12: PvP disconnect grace period + auto-resign

**Files:**
- Create: `backend/tests/test_disconnect_grace.py`
- Modify: `backend/game/socket_handlers.py` (schedule grace on disconnect)

**Interfaces:**
- Consumes: `manager.active_pvp_game_ids_for_user`, `manager.schedule_disconnect_grace`, `manager._disconnect_grace` (Task 8).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_disconnect_grace.py
from extensions import db
from models import Game
from game import manager


def test_disconnect_grace_auto_resigns_if_not_reconnected(app, make_user, monkeypatch):
    monkeypatch.setattr(manager.socketio, "sleep", lambda s: None)
    alice = make_user(email="a@example.com", display_name="Alice")
    bob = make_user(email="b@example.com", display_name="Bob")
    game = manager.create_pvp_game(alice.id, bob.id)

    manager._disconnect_grace(game.id, alice.id, lambda: False)

    refreshed = db.session.get(Game, game.id)
    assert refreshed.status == "resigned"
    assert refreshed.state_json["result"]["winner"] == 1


def test_disconnect_grace_noop_if_reconnected(app, make_user, monkeypatch):
    monkeypatch.setattr(manager.socketio, "sleep", lambda s: None)
    alice = make_user(email="a2@example.com", display_name="Alice2")
    bob = make_user(email="b2@example.com", display_name="Bob2")
    game = manager.create_pvp_game(alice.id, bob.id)

    manager._disconnect_grace(game.id, alice.id, lambda: True)

    refreshed = db.session.get(Game, game.id)
    assert refreshed.status == "active"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_disconnect_grace.py -v`
Expected: FAIL — `manager._disconnect_grace` exists from Task 8 already, so check this actually passes already; if so this task's real gap is that `on_disconnect` never *calls* it yet. Confirm by grepping: `grep -n "schedule_disconnect_grace" backend/game/socket_handlers.py` should return nothing before Step 3.

- [ ] **Step 3: Wire disconnect scheduling into the socket handler**

```python
# backend/game/socket_handlers.py — replace on_disconnect body:
    @socketio_instance.on("disconnect", namespace="/game")
    def on_disconnect():
        user_id = _sid_user.pop(request.sid, None)
        if user_id is None:
            return
        matchmaking.leave_queue(user_id)
        _connected_users.discard(user_id)
        for game_id in manager.active_pvp_game_ids_for_user(user_id):
            manager.schedule_disconnect_grace(
                game_id, user_id, lambda uid=user_id: uid in _connected_users
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_disconnect_grace.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && python -m pytest -v`
Expected: all tests PASS (this is the last backend task — confirm the whole suite is green)

- [ ] **Step 6: Commit**

```bash
git add backend/game/socket_handlers.py backend/tests/test_disconnect_grace.py
git commit -m "feat: auto-resign disconnected PvP players after a 30s grace period"
```

---

## Task 13: Frontend app shell (routing, auth, socket context, header)

**Files:**
- Create: `frontend/src/api/client.js`
- Create: `frontend/src/context/AuthContext.jsx`
- Create: `frontend/src/context/SocketContext.jsx`
- Create: `frontend/src/context/GameContext.jsx`
- Create: `frontend/src/components/Header.jsx`
- Create: `frontend/src/pages/Lobby.jsx` (stub, filled in Task 14)
- Create: `frontend/src/pages/Table.jsx` (stub, filled in Task 15)
- Create: `frontend/src/pages/Rules.jsx` (stub, filled in Task 16)
- Create: `frontend/src/pages/Leaderboard.jsx` (stub, filled in Task 16)
- Create: `frontend/src/pages/Profile.jsx` (stub, filled in Task 16)
- Create: `frontend/src/pages/SignedOut.jsx` (stub, filled in Task 14)
- Modify: `frontend/src/App.jsx` (replace placeholder with full router)

**Interfaces:**
- Consumes: `/api/auth/*` (Task 5), `/game` Socket.IO namespace (Task 9).
- Produces: `useAuth()` (`{token, user, loading, login, signup, logout}`), `useSocket()` (a connected `socket.io-client` instance or `null`), `useGame()` (`{gameState, error, act(type, payload)}`) — consumed by every page task from here on.

**Design note (from plan pre-flight review):** `game_state` must be subscribed to exactly once, at a point that stays mounted across the Lobby→Table navigation — not inside `Table.jsx` itself. If `Table.jsx` subscribed on its own mount, a PvP match (server emits `match_found` and `game_state` back-to-back the instant two players pair, per Task 11) could have its `game_state` event arrive and be dropped before `Table.jsx` finishes mounting, leaving the table stuck on "Setting up the table…". `GameContext` is mounted once at the `Shell` level (above the router), so it is always listening before any `game_state` event can be emitted, in both the bot and PvP flows.

- [ ] **Step 1: Write the API client**

```js
// frontend/src/api/client.js
const BASE = '/api'

function authHeaders() {
  const token = localStorage.getItem('rw_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...(options.headers || {}),
    },
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(body.error || 'Request failed')
  return body
}

export const api = {
  signup: (data) => request('/auth/signup', { method: 'POST', body: JSON.stringify(data) }),
  login: (data) => request('/auth/login', { method: 'POST', body: JSON.stringify(data) }),
  me: () => request('/auth/me'),
  leaderboard: () => request('/leaderboard'),
  profile: () => request('/profile'),
}
```

- [ ] **Step 2: Write AuthContext**

```jsx
// frontend/src/context/AuthContext.jsx
import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { api } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('rw_token'))
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) { setLoading(false); return }
    api.me()
      .then(setUser)
      .catch(() => { setToken(null); localStorage.removeItem('rw_token') })
      .finally(() => setLoading(false))
  }, [token])

  const login = useCallback(async (email, password) => {
    const { token: t, user: u } = await api.login({ email, password })
    localStorage.setItem('rw_token', t)
    setToken(t)
    setUser(u)
  }, [])

  const signup = useCallback(async (email, password, display_name) => {
    const { token: t, user: u } = await api.signup({ email, password, display_name })
    localStorage.setItem('rw_token', t)
    setToken(t)
    setUser(u)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('rw_token')
    setToken(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ token, user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
```

- [ ] **Step 3: Write SocketContext**

```jsx
// frontend/src/context/SocketContext.jsx
import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { io } from 'socket.io-client'
import { useAuth } from './AuthContext'

const SocketContext = createContext(null)

export function SocketProvider({ children }) {
  const { token } = useAuth()
  const [socket, setSocket] = useState(null)
  const ref = useRef(null)

  useEffect(() => {
    if (!token) {
      ref.current?.disconnect()
      ref.current = null
      setSocket(null)
      return
    }
    const s = io('/game', { auth: { token } })
    ref.current = s
    setSocket(s)
    return () => s.disconnect()
  }, [token])

  return <SocketContext.Provider value={socket}>{children}</SocketContext.Provider>
}

export function useSocket() {
  return useContext(SocketContext)
}
```

- [ ] **Step 4: Write GameContext**

```jsx
// frontend/src/context/GameContext.jsx
import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { useSocket } from './SocketContext'

const GameContext = createContext(null)

export function GameProvider({ children }) {
  const socket = useSocket()
  const [gameState, setGameState] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!socket) { setGameState(null); return }
    const onState = (s) => setGameState(s)
    const onError = (e) => setError(e.message)
    socket.on('game_state', onState)
    socket.on('error', onError)
    return () => {
      socket.off('game_state', onState)
      socket.off('error', onError)
    }
  }, [socket])

  const act = useCallback((type, payload) => {
    if (!socket || !gameState) return
    socket.emit('action', { game_id: gameState.game_id, type, payload })
  }, [socket, gameState])

  return (
    <GameContext.Provider value={{ gameState, error, act }}>
      {children}
    </GameContext.Provider>
  )
}

export function useGame() {
  return useContext(GameContext)
}
```

- [ ] **Step 5: Write Header**

```jsx
// frontend/src/components/Header.jsx
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const navLinkStyle = {
  font: "700 13px 'Archivo', sans-serif", color: '#1c1a14', background: 'transparent',
  border: '1px solid transparent', borderRadius: 2, padding: '8px 12px',
  cursor: 'pointer', textDecoration: 'none',
}

export default function Header() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const initials = (user?.display_name || 'G').slice(0, 2).toUpperCase()

  const menuItems = [
    { label: 'Profile / stats', act: () => { setOpen(false); navigate('/profile') } },
    { label: 'Help & rules', act: () => { setOpen(false); navigate('/rules') } },
    { label: 'Log out', act: () => { setOpen(false); logout(); navigate('/signed-out') } },
  ]

  return (
    <header style={{ position: 'sticky', top: 0, zIndex: 40, display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap', padding: '10px 18px', background: '#f4f0e6', borderBottom: '1px solid #c9c2b1' }}>
      <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none', color: 'inherit', flex: '0 0 auto' }}>
        <div style={{ width: 34, height: 34, borderRadius: 2, background: '#16150f', display: 'grid', placeItems: 'center' }}>
          <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M5 19c0-7 6-4.5 6-10a3.2 3.2 0 016.4 0" fill="none" stroke="#a8232b" strokeWidth="4" strokeLinecap="round" /></svg>
        </div>
        <span style={{ fontWeight: 900, letterSpacing: '.3px', fontSize: 19, color: '#16150f' }}>Regenwormen</span>
      </Link>

      <nav style={{ display: 'flex', alignItems: 'center', gap: 4, flex: '1 1 auto', flexWrap: 'wrap' }}>
        <Link to="/table" style={navLinkStyle}>New game</Link>
        <Link to="/rules" style={navLinkStyle}>Game rules</Link>
        <Link to="/leaderboard" style={navLinkStyle}>Leaderboard</Link>
      </nav>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: '0 0 auto' }}>
        {user ? (
          <div style={{ position: 'relative' }}>
            <button onClick={() => setOpen(o => !o)} style={{ display: 'flex', alignItems: 'center', gap: 9, background: '#ded7c5', border: '1px solid #c3bbaa', borderRadius: 999, padding: '5px 12px 5px 5px', cursor: 'pointer', color: '#1c1a14' }}>
              <span style={{ width: 28, height: 28, borderRadius: 999, background: '#a8232b', color: '#fff', display: 'grid', placeItems: 'center', fontWeight: 900, fontSize: 12 }}>{initials}</span>
              <span style={{ fontWeight: 700, fontSize: 13 }}>{user.display_name}</span>
              <span style={{ fontSize: 10, opacity: .7 }}>&#9662;</span>
            </button>
            {open && (
              <div style={{ position: 'absolute', right: 0, top: 'calc(100% + 8px)', width: 232, background: '#f4f0e6', border: '1px solid #c3bbaa', borderRadius: 2, padding: 8 }}>
                <div style={{ padding: '8px 10px 10px', borderBottom: '1px solid #ded7c5', marginBottom: 6 }}>
                  <div style={{ fontWeight: 900, fontSize: 14 }}>{user.display_name}</div>
                  <div style={{ fontSize: 12, color: '#54504a' }}>{user.email}</div>
                </div>
                {menuItems.map(item => (
                  <button key={item.label} onClick={item.act} style={{ width: '100%', textAlign: 'left', background: 'transparent', border: 0, borderRadius: 2, padding: '9px 10px', color: '#1c1a14', fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>
                    {item.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <Link to="/signed-out" style={{ ...navLinkStyle, background: '#a8232b', color: '#fff' }}>Sign in</Link>
        )}
      </div>
    </header>
  )
}
```

Note: the original design shows a "Remise" (resign) button in the header at all times. This plan moves it into `Table.jsx` (Task 15) instead, shown only during an active game — a deliberate simplification since the header has no game context outside `/table`.

- [ ] **Step 6: Write page stubs**

```jsx
// frontend/src/pages/Lobby.jsx
export default function Lobby() { return <div style={{ padding: 40 }}>Lobby (coming soon)</div> }
```

```jsx
// frontend/src/pages/Table.jsx
export default function Table() { return <div style={{ padding: 40 }}>Table (coming soon)</div> }
```

```jsx
// frontend/src/pages/Rules.jsx
export default function Rules() { return <div style={{ padding: 40 }}>Rules (coming soon)</div> }
```

```jsx
// frontend/src/pages/Leaderboard.jsx
export default function Leaderboard() { return <div style={{ padding: 40 }}>Leaderboard (coming soon)</div> }
```

```jsx
// frontend/src/pages/Profile.jsx
export default function Profile() { return <div style={{ padding: 40 }}>Profile (coming soon)</div> }
```

```jsx
// frontend/src/pages/SignedOut.jsx
export default function SignedOut() { return <div style={{ padding: 40 }}>Signed out (coming soon)</div> }
```

- [ ] **Step 7: Replace App.jsx with the full router**

```jsx
// frontend/src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { SocketProvider } from './context/SocketContext'
import { GameProvider } from './context/GameContext'
import Header from './components/Header'
import Lobby from './pages/Lobby'
import Table from './pages/Table'
import Rules from './pages/Rules'
import Leaderboard from './pages/Leaderboard'
import Profile from './pages/Profile'
import SignedOut from './pages/SignedOut'

function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  return user ? children : <Navigate to="/signed-out" replace />
}

function Shell() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', fontFamily: "'Archivo', system-ui, sans-serif", color: '#1c1a14', background: '#e9e3d5' }}>
      <Header />
      <main style={{ flex: '1 1 auto', display: 'flex', flexDirection: 'column' }}>
        <Routes>
          <Route path="/" element={<Lobby />} />
          <Route path="/table" element={<RequireAuth><Table /></RequireAuth>} />
          <Route path="/rules" element={<Rules />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
          <Route path="/profile" element={<RequireAuth><Profile /></RequireAuth>} />
          <Route path="/signed-out" element={<SignedOut />} />
        </Routes>
      </main>
      <footer style={{ padding: '22px 20px 30px', textAlign: 'center', font: "400 12px 'Archivo', sans-serif", color: '#77736a', borderTop: '1px solid #c9c2b1' }}>
        Fan-made table for Regenwormen. Prototype.
      </footer>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <SocketProvider>
          <GameProvider>
            <Shell />
          </GameProvider>
        </SocketProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
```

- [ ] **Step 8: Verify the shell boots and routes render**

Run: `docker compose up -d --build && sleep 20 && curl -s http://localhost:5173/ | grep -o '<title>[^<]*</title>'`
Expected: `<title>Regenwormen</title>`

Manual check in a browser at `http://localhost:5173/`: header shows "Regenwormen" / "New game" / "Game rules" / "Leaderboard" / "Sign in"; clicking "Game rules" navigates to the Rules stub; clicking "Sign in" navigates to the SignedOut stub. Clicking "New game" while signed out redirects to `/signed-out` (RequireAuth).

Run: `docker compose down`

- [ ] **Step 9: Commit**

```bash
git add frontend/src
git commit -m "feat: add frontend app shell, auth/socket/game contexts, and routing"
```

---

## Task 14: Lobby + sign-in/sign-up flow

**Files:**
- Modify: `frontend/src/pages/Lobby.jsx`
- Modify: `frontend/src/pages/SignedOut.jsx`

**Interfaces:**
- Consumes: `useAuth()`, `useSocket()` (Task 13).

- [ ] **Step 1: Write the sign-in/sign-up form**

```jsx
// frontend/src/pages/SignedOut.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const inputStyle = { width: '100%', padding: '11px 12px', marginBottom: 10, border: '1px solid #c3bbaa', borderRadius: 2, font: "400 14px 'Archivo', sans-serif" }

export default function SignedOut() {
  const { login, signup } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState('')

  async function submit(e) {
    e.preventDefault()
    setError('')
    try {
      if (mode === 'login') await login(email, password)
      else await signup(email, password, displayName)
      navigate('/')
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <section style={{ flex: '1 1 auto', display: 'grid', placeItems: 'center', padding: '60px 20px' }}>
      <form onSubmit={submit} style={{ maxWidth: 360, width: '100%', textAlign: 'center', padding: '34px 26px', borderRadius: 2, background: '#f4f0e6', border: '1px solid #ded7c5' }}>
        <h1 style={{ fontWeight: 900, fontSize: 26, margin: '0 0 8px', color: '#16150f' }}>{mode === 'login' ? 'Sign in' : 'Create account'}</h1>
        <p style={{ fontSize: 15, lineHeight: 1.6, color: '#54504a', margin: '0 0 22px' }}>Sign in to keep playing.</p>
        {mode === 'signup' && (
          <input value={displayName} onChange={e => setDisplayName(e.target.value)} placeholder="Display name" required style={inputStyle} />
        )}
        <input value={email} onChange={e => setEmail(e.target.value)} type="email" placeholder="Email" required style={inputStyle} />
        <input value={password} onChange={e => setPassword(e.target.value)} type="password" placeholder="Password" required style={inputStyle} />
        {error && <div style={{ color: '#a8232b', fontSize: 13, marginBottom: 12 }}>{error}</div>}
        <button type="submit" style={{ width: '100%', font: "900 14px 'Archivo', sans-serif", color: '#ffffff', background: '#a8232b', border: 0, borderBottom: '3px solid #7a1a20', borderRadius: 2, padding: '14px 20px', cursor: 'pointer' }}>
          {mode === 'login' ? 'Sign in' : 'Create account'}
        </button>
        <button type="button" onClick={() => setMode(m => m === 'login' ? 'signup' : 'login')} style={{ marginTop: 12, background: 'none', border: 0, color: '#a8232b', cursor: 'pointer', font: "700 13px 'Archivo', sans-serif" }}>
          {mode === 'login' ? 'Need an account? Sign up' : 'Have an account? Sign in'}
        </button>
      </form>
    </section>
  )
}
```

- [ ] **Step 2: Write the Lobby**

```jsx
// frontend/src/pages/Lobby.jsx
import { useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { useSocket } from '../context/SocketContext'

const primaryBtn = { font: "900 14px 'Archivo', sans-serif", color: '#ffffff', background: '#a8232b', border: 0, borderBottom: '3px solid #7a1a20', borderRadius: 2, padding: '15px 22px', cursor: 'pointer' }
const secondaryBtn = { font: "900 14px 'Archivo', sans-serif", color: '#1c1a14', background: '#ded7c5', border: '1px solid #b3ab99', borderBottom: '3px solid #8e1c22', borderRadius: 2, padding: '15px 22px', cursor: 'pointer' }

export default function Lobby() {
  const { user } = useAuth()
  const socket = useSocket()
  const navigate = useNavigate()
  const [matchmaking, setMatchmaking] = useState(false)

  useEffect(() => {
    if (!socket) return
    const onMatchFound = () => { setMatchmaking(false); navigate('/table') }
    socket.on('match_found', onMatchFound)
    return () => socket.off('match_found', onMatchFound)
  }, [socket, navigate])

  function playBot() {
    if (!user) { navigate('/signed-out'); return }
    socket.emit('start_bot_game')
    navigate('/table')
  }

  function playOnline() {
    if (!user) { navigate('/signed-out'); return }
    setMatchmaking(true)
    socket.emit('find_match')
  }

  return (
    <section style={{ flex: '1 1 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 28, alignItems: 'center', maxWidth: 1120, width: '100%', margin: '0 auto', padding: '40px 20px 56px' }}>
      <div>
        <div style={{ fontWeight: 900, fontSize: 12, letterSpacing: '.18em', textTransform: 'uppercase', color: '#a8232b' }}>Two players &middot; eight dice &middot; sixteen tiles</div>
        <h1 style={{ fontWeight: 900, letterSpacing: '-.015em', fontSize: 'clamp(34px, 6vw, 58px)', lineHeight: 1.02, margin: '12px 0 14px', color: '#16150f' }}>Regenwormen in the browser</h1>
        <p style={{ fontSize: 16, lineHeight: 1.6, color: '#4a473f', maxWidth: '46ch', margin: '0 0 26px' }}>Set dice aside, stop in time, and claim the tile that matches your score. Play the bot, or wait for someone online to sit down.</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
          <button onClick={playBot} style={primaryBtn}>Play the bot</button>
          <button onClick={playOnline} style={secondaryBtn}>Find an opponent</button>
        </div>
        {matchmaking && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 20, fontWeight: 600, fontSize: 13, color: '#a8232b' }}>
            <span style={{ width: 15, height: 15, border: '2px solid #b3ab99', borderTopColor: '#a8232b', borderRadius: 999, display: 'inline-block', animation: 'rw-spin .8s linear infinite' }} />
            Looking for an opponent
          </div>
        )}
      </div>
      <div style={{ borderRadius: 2, overflow: 'hidden', border: '1px solid #c9c2b1' }}>
        <img src="/regenwormen-tiles.png" alt="Regenwormen tiles and dice on a table" style={{ display: 'block', width: '100%', height: 'auto' }} />
      </div>
    </section>
  )
}
```

- [ ] **Step 3: Verify the hero image is served**

Run: `docker compose up -d --build && sleep 20 && curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/regenwormen-tiles.png`
Expected: `200`

- [ ] **Step 4: Manual verification**

In a browser at `http://localhost:5173/`: sign up with a new email/password/display name → redirected to lobby, header now shows your initials and name. Click "Play the bot" while signed in → navigates to `/table` (still a stub, wired fully in Task 15). Log out via the header menu → redirected to `/signed-out`; sign back in with the same credentials succeeds.

Run: `docker compose down`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Lobby.jsx frontend/src/pages/SignedOut.jsx
git commit -m "feat: wire Lobby and sign-in/sign-up flow to real auth"
```

---

## Task 15: Table page — full bot gameplay

**Files:**
- Modify: `frontend/src/pages/Table.jsx`

**Interfaces:**
- Consumes: `useAuth()`, `useSocket()`, `useGame()` (Task 13); the `game_state`/`error` events and `action`/`start_bot_game` emits defined by `game/socket_handlers.py` (Task 9).

- [ ] **Step 1: Write the full Table component**

```jsx
// frontend/src/pages/Table.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useSocket } from '../context/SocketContext'
import { useGame } from '../context/GameContext'

const PIPS = {
  1: [[50, 50]], 2: [[28, 28], [72, 72]], 3: [[26, 26], [50, 50], [74, 74]],
  4: [[30, 30], [70, 30], [30, 70], [70, 70]],
  5: [[30, 30], [70, 30], [50, 50], [30, 70], [70, 70]],
}
const wormsOn = n => (n <= 24 ? 1 : n <= 28 ? 2 : n <= 32 ? 3 : 4)
const val = f => (f === 'w' ? 5 : f)

const primaryBtn = { font: "900 13px 'Archivo', sans-serif", color: '#fff', background: '#a8232b', border: 0, borderBottom: '3px solid #7a1a20', borderRadius: 2, padding: '12px 18px', cursor: 'pointer' }
const mutedBtn = { font: "900 13px 'Archivo', sans-serif", color: '#1c1a14', background: '#ded7c5', border: '1px solid #b3ab99', borderRadius: 2, padding: '12px 18px', cursor: 'pointer' }
const resignBtn = { font: "900 12px 'Archivo', sans-serif", letterSpacing: '.1em', textTransform: 'uppercase', color: '#fff', background: '#a8232b', border: '1px solid #6f1319', borderRadius: 2, padding: '9px 14px', cursor: 'pointer' }
const overlayStyle = { position: 'fixed', inset: 0, zIndex: 60, background: 'rgba(10,7,4,.75)', display: 'grid', placeItems: 'center', padding: 20 }
const dialogStyle = { maxWidth: 400, width: '100%', padding: 28, borderRadius: 2, background: '#f4f0e6', border: '1px solid #c3bbaa' }

function Die({ face, live, onClick }) {
  const isWorm = face === 'w'
  return (
    <button onClick={onClick} disabled={!live} style={{
      position: 'relative', width: 48, height: 48, borderRadius: 9, background: '#fdfdfb',
      border: `1px solid ${live ? '#c2b7a3' : '#9a9182'}`, cursor: live ? 'pointer' : 'default',
      filter: live ? 'none' : 'grayscale(1) brightness(.72) contrast(.9)', padding: 0,
    }}>
      {isWorm
        ? <svg viewBox="0 0 24 24" width="30" height="30" aria-hidden="true"><path d="M5 19c0-7 6-4.5 6-10a3.2 3.2 0 016.4 0" fill="none" stroke="#a8232b" strokeWidth="4.5" strokeLinecap="round" /></svg>
        : PIPS[face].map(([x, y], i) => (
          <span key={i} style={{ position: 'absolute', width: 8, height: 8, borderRadius: 999, background: '#2b3a8f', left: `${x}%`, top: `${y}%`, transform: 'translate(-50%, -50%)' }} />
        ))}
    </button>
  )
}

export default function Table() {
  const { user } = useAuth()
  const socket = useSocket()
  const { gameState: state, act } = useGame()
  const navigate = useNavigate()
  const [confirmOpen, setConfirmOpen] = useState(false)

  if (!state) {
    return <div style={{ padding: 40, textAlign: 'center', color: '#54504a' }}>Setting up the table&hellip;</div>
  }

  const myIdx = user.id === state.player1_id ? 0 : 1
  const myTurn = state.turn === myIdx && !state.result
  const score = state.aside.reduce((t, f) => t + val(f), 0)
  const selectable = new Set(state.roll.filter(f => !state.aside.includes(f)))
  const canRoll = myTurn && state.roll.length === 0 && state.aside.length < 8
  const claimable = myTurn && state.roll.length === 0 && state.aside.length > 0
  const names = [state.player1_name, state.player2_name]
  const stacks = state.stacks

  function resign() {
    act('resign')
    setConfirmOpen(false)
  }

  return (
    <section style={{ flex: '1 1 auto', background: '#a97743', padding: '18px 16px 30px' }}>
      <div style={{ maxWidth: 1080, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 16 }}>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
          {[0, 1].map(idx => {
            const stack = stacks[idx]
            const worms = stack.reduce((t, n) => t + wormsOn(n), 0)
            const active = state.turn === idx && !state.result
            const topTile = stack.length ? stack[stack.length - 1] : null
            const stealable = idx !== myIdx && claimable && topTile !== null && score === topTile && state.aside.includes('w')
            return (
              <div key={idx} style={{ flex: '1 1 220px', display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px', borderRadius: 2, background: active ? 'rgba(255,255,255,.9)' : 'rgba(255,255,255,.62)', border: `1px solid ${active ? '#a8232b' : 'rgba(255,255,255,.35)'}` }}>
                <span style={{ width: 34, height: 34, borderRadius: 999, background: idx === 0 ? '#a8232b' : '#2b3a8f', color: '#fff', display: 'grid', placeItems: 'center', fontWeight: 900, fontSize: 13 }}>
                  {(names[idx] || '?').slice(0, 2).toUpperCase()}
                </span>
                <div style={{ flex: '1 1 auto', minWidth: 0 }}>
                  <div style={{ fontWeight: 900, fontSize: 14, color: '#2a1c10', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {names[idx]}{idx === myIdx ? ' (you)' : ''}
                  </div>
                  <div style={{ fontWeight: 600, fontSize: 12, color: '#6b5541' }}>{stack.length} tiles &middot; {worms} worms{active ? ' &middot; to move' : ''}</div>
                </div>
                {topTile !== null && (
                  <div
                    onClick={() => stealable && act('claim', { kind: 'steal', num: topTile })}
                    title={stealable ? `Click to steal tile ${topTile}` : `Top tile: ${topTile}`}
                    style={{
                      width: 44, padding: '9px 0 11px', borderRadius: 5, background: '#f7f1e1',
                      border: `2px solid ${stealable ? '#a8232b' : 'transparent'}`,
                      boxShadow: '0 2px 4px rgba(0,0,0,.3), inset 0 -2px 0 rgba(0,0,0,.08)',
                      textAlign: 'center', cursor: stealable ? 'pointer' : 'default',
                    }}
                  >
                    <div style={{ fontWeight: 900, fontSize: 16, color: '#1d2a4a' }}>{topTile}</div>
                    <div style={{ height: 1, background: '#1d2a4a', margin: '3px 7px' }} />
                    <div style={{ display: 'flex', justifyContent: 'center', gap: 1, paddingTop: 3 }}>
                      {Array.from({ length: wormsOn(topTile) }).map((_, i) => (
                        <svg key={i} viewBox="0 0 24 24" width="9" height="9" aria-hidden="true"><path d="M5 19c0-7 6-4.5 6-10a3.2 3.2 0 016.4 0" fill="none" stroke="#a8232b" strokeWidth="4.5" strokeLinecap="round" /></svg>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        <div style={{ padding: 14, borderRadius: 2, background: 'rgba(255,255,255,.14)', border: '1px solid rgba(255,255,255,.22)' }}>
          <div style={{ fontWeight: 900, fontSize: 11, letterSpacing: '.16em', textTransform: 'uppercase', color: '#4b3722', marginBottom: 10 }}>Tiles in the middle</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {Array.from({ length: 16 }, (_, i) => 21 + i).map(n => {
              const here = state.center.includes(n)
              const gone = state.out.includes(n)
              const maxTakeable = Math.max(-1, ...state.center.filter(c => c <= score))
              const pickable = claimable && score >= n && state.aside.includes('w') && here && n === maxTakeable
              return (
                <div key={n} onClick={() => pickable && act('claim', { kind: 'take', num: n })} style={{
                  width: 56, padding: '13px 0 15px', borderRadius: 6, textAlign: 'center',
                  background: here ? '#f7f1e1' : 'rgba(0,0,0,.13)',
                  border: `2px solid ${pickable ? '#3f7d4f' : 'transparent'}`,
                  opacity: gone ? 0.35 : 1, cursor: pickable ? 'pointer' : 'default',
                }}>
                  <div style={{ fontWeight: 900, fontSize: 21, color: here ? '#1d2a4a' : 'rgba(255,255,255,.35)' }}>{n}</div>
                  <div style={{ height: 1, background: here ? '#1d2a4a' : 'rgba(255,255,255,.22)', margin: '4px 9px' }} />
                  <div style={{ display: 'flex', justifyContent: 'center', gap: 1, minHeight: 26, paddingTop: 4, flexWrap: 'wrap' }}>
                    {here && Array.from({ length: wormsOn(n) }).map((_, i) => (
                      <svg key={i} viewBox="0 0 24 24" width="12" height="12" aria-hidden="true"><path d="M5 19c0-7 6-4.5 6-10a3.2 3.2 0 016.4 0" fill="none" stroke="#a8232b" strokeWidth="4.5" strokeLinecap="round" /></svg>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
          <div style={{ padding: 16, borderRadius: 2, background: 'rgba(28,18,10,.5)', border: '1px solid rgba(255,255,255,.14)' }}>
            <div style={{ fontWeight: 900, fontSize: 11, letterSpacing: '.16em', textTransform: 'uppercase', color: '#d9b98e', marginBottom: 12 }}>
              Your roll &middot; {state.result ? 'game over' : myTurn ? (state.roll.length ? 'choose a value' : 'your move') : `${names[1 - myIdx]}’s turn`}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, minHeight: 56 }}>
              {state.roll.map((f, i) => (
                <Die key={i} face={f} live={myTurn && selectable.has(f)} onClick={() => act('pick', { face: f })} />
              ))}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 16 }}>
              {canRoll && <button onClick={() => act('roll')} style={primaryBtn}>Roll {8 - state.aside.length} dice</button>}
              {claimable && state.aside.length === 8 && <button onClick={() => act('stop')} style={mutedBtn}>Stop</button>}
              {!state.result && <button onClick={() => setConfirmOpen(true)} style={resignBtn}>Remise</button>}
            </div>
          </div>

          <div style={{ padding: 16, borderRadius: 2, background: 'rgba(28,18,10,.5)', border: '1px solid rgba(255,255,255,.14)' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12, marginBottom: 12 }}>
              <div style={{ fontWeight: 900, fontSize: 11, letterSpacing: '.16em', textTransform: 'uppercase', color: '#d9b98e' }}>Set aside</div>
              <div style={{ fontWeight: 900, fontSize: 26, color: '#f7f1e1' }}>{score}</div>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, minHeight: 56 }}>
              {state.aside.map((f, i) => <Die key={i} face={f} live={false} onClick={() => {}} />)}
            </div>
            <div style={{ marginTop: 16, borderTop: '1px solid rgba(255,255,255,.12)', paddingTop: 12 }}>
              <div style={{ fontWeight: 900, fontSize: 11, letterSpacing: '.16em', textTransform: 'uppercase', color: '#d9b98e', marginBottom: 8 }}>Turn log</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 5, maxHeight: 132, overflow: 'auto' }}>
                {state.log.map((line, i) => <div key={i} style={{ fontSize: 12, lineHeight: 1.4, color: '#bda98f' }}>{line.text}</div>)}
              </div>
            </div>
          </div>
        </div>
      </div>

      {confirmOpen && (
        <div style={overlayStyle}>
          <div style={dialogStyle}>
            <h2 style={{ fontWeight: 900, fontSize: 22, margin: '0 0 8px', color: '#16150f' }}>Remise, resign this game?</h2>
            <p style={{ fontSize: 15, lineHeight: 1.6, color: '#54504a', margin: '0 0 22px' }}>Your tiles go back to the middle and the game is scored as a loss.</p>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <button onClick={resign} style={{ ...resignBtn, flex: '1 1 130px' }}>Resign</button>
              <button onClick={() => setConfirmOpen(false)} style={{ ...mutedBtn, flex: '1 1 130px' }}>Keep playing</button>
            </div>
          </div>
        </div>
      )}

      {state.result && (
        <div style={overlayStyle}>
          <div style={{ ...dialogStyle, textAlign: 'center' }}>
            <h2 style={{ fontWeight: 900, fontSize: 28, margin: '0 0 10px', color: '#a8232b' }}>
              {state.result.winner === null ? 'Draw' : state.result.winner === myIdx ? 'You win!' : `${names[1 - myIdx]} wins`}
            </h2>
            <p style={{ fontSize: 15, lineHeight: 1.6, color: '#4a473f', margin: '0 0 24px' }}>
              Final count: {names[0]} {state.result.worms[0]} worms, {names[1]} {state.result.worms[1]} worms.
            </p>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <button onClick={() => socket.emit('start_bot_game')} style={{ ...primaryBtn, flex: '1 1 130px' }}>Play again</button>
              <button onClick={() => navigate('/')} style={{ ...mutedBtn, flex: '1 1 130px' }}>Back to lobby</button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
```

- [ ] **Step 2: Manual verification — full bot game**

`docker compose up -d --build`, sign up in the browser, click "Play the bot" from the Lobby. Verify: rolling deals 8 dice; clicking a die value sets aside all dice of that value and greys out the roll; "Roll N dice" reappears for the remainder; once you have a worm set aside and a valid score, the matching center tile highlights green and is clickable; clicking it claims the tile and the bot's turn runs automatically with visible dice/log updates; play continues until the center is empty and the result dialog shows a winner with correct worm counts; "Play again" starts a fresh bot game; "Remise" opens the confirm dialog and resigning ends the game as a loss. Also verify stealing: play until the bot has claimed at least one tile, then on a later turn roll/pick until your set-aside score exactly matches the bot's top (most recently claimed) tile — its tile in the bot's seat card should outline red and be clickable, and clicking it moves that tile from the bot's stack to yours (check the log line reads "... stole tile N!").

Run: `docker compose down`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Table.jsx
git commit -m "feat: wire Table page to real server-authoritative bot gameplay"
```

---

## Task 16: Rules, Leaderboard, and Profile pages

**Files:**
- Modify: `frontend/src/pages/Rules.jsx`
- Modify: `frontend/src/pages/Leaderboard.jsx`
- Modify: `frontend/src/pages/Profile.jsx`

**Interfaces:**
- Consumes: `api.leaderboard()`, `api.profile()` (Task 5/10 REST endpoints via the Task 13 API client), `useAuth()`.

- [ ] **Step 1: Write the Rules page**

```jsx
// frontend/src/pages/Rules.jsx
const h2 = { fontWeight: 900, letterSpacing: '-.015em', fontSize: 24, lineHeight: 1.2, margin: '40px 0 12px', color: '#a8232b' }
const p = { fontSize: 16, lineHeight: 1.7, color: '#4a473f' }

export default function Rules() {
  return (
    <section style={{ maxWidth: 760, margin: '0 auto', padding: '44px 20px 70px' }}>
      <h1 style={{ fontWeight: 900, letterSpacing: '-.015em', fontSize: 'clamp(30px, 5vw, 46px)', lineHeight: 1.06, margin: '0 0 20px', color: '#16150f' }}>Regenwormen spelregels</h1>
      <p style={{ ...p, fontSize: 18 }}>Regenwormen, het spel dat spannend blijft tot de laatste worp! In dit strategische dobbelspel voel je je warempel zo nu en dan zelf bijna een regenworm, kronkelend tussen kansen en risico&rsquo;s, terwijl je probeert zoveel mogelijk tegels met zoveel mogelijk wormen te verzamelen.</p>
      <p style={p}>Met acht dobbelstenen en een flinke stapel tegeltjes biedt Regenwormen een perfecte mix van geluk en tactiek, waarmee zowel kinderen als volwassenen zich urenlang kunnen vermaken. Geen enkele speelronde is hetzelfde, want &eacute;&eacute;n worp te veel kan je van winnaar tot verliezer transformeren!</p>

      <h2 style={h2}>Wat heb je nodig voor een glibberige Regenwormen-sessie?</h2>
      <p style={p}>Voor je wormenfeest heb je natuurlijk het basisspel nodig met z&rsquo;n speciale dobbelstenen en wormentegels. Die 16 tegels zijn genummerd van 21 tot en met 36, en er staan verschillend aantallen regenwormen op. Je kunt het spel spelen met 2 tot 7 spelers, maar het meest ideaal is 3 tot 5 spelers. Op die manier heb je meer kansen om tegels van elkaar te stelen, en dat is nou precies waar de grootste lol zit!</p>
      <p style={{ ...p, fontStyle: 'italic', color: '#54504a', borderLeft: '3px solid #b3ab99', paddingLeft: 16, margin: '22px 0' }}>(Waarom dobbelstenen met regenwormen? Omdat deze kleine glibberige vrienden niet alleen schattig zijn, maar ook de meest waardevolle punten vertegenwoordigen in dit spel. Je zou kunnen zeggen dat de regenworm de aas is in dit kaartspel zonder kaarten!)</p>

      <h2 style={h2}>Voorbereiding: sneller dan een regenworm die in de grond verdwijnt</h2>
      <p style={p}>De voorbereiding is zo eenvoudig dat zelfs een regenworm het zou begrijpen. Leg alle zestien tegels netjes op volgorde in het midden van de tafel, met de laagste waarde (21) helemaal links en de hoogste waarde (36) uiterst rechts. Geef de acht dobbelstenen aan de startspeler, et voil&agrave;! Je bent klaar om te wormen.</p>
      <p style={p}>De startspeler is degene die het meest recent een regenworm in het echt heeft gezien. Geen recente wormenwaarnemingen? Dan begint de jongste speler. Klinkt willekeurig, maar dat is precies de sfeer die we zoeken bij dit spel.</p>
      <figure style={{ margin: '26px 0 0' }}>
        <img src="/regenwormen-tiles.png" alt="Regenwormen" style={{ display: 'block', width: '100%', height: 'auto', borderRadius: 2, border: '1px solid #c9c2b1' }} />
        <figcaption style={{ fontSize: 12, fontWeight: 600, color: '#6d6961', marginTop: 8 }}>Regenwormen</figcaption>
      </figure>

      <h2 style={h2}>Tijd om te wormen!</h2>
      <h3 style={{ fontWeight: 900, fontSize: 15, letterSpacing: '.12em', textTransform: 'uppercase', color: '#a8232b', margin: '0 0 12px' }}>De kunst van het dobbelen en selecteren</h3>
      <p style={p}>Als actieve speler werp je alle acht dobbelstenen. Na je worp moet je een beslissing nemen: welke dobbelstenen leg je apart? Je moet kiezen voor alle dobbelstenen met dezelfde waarde OF alle dobbelstenen met een regenworm. Leg deze dobbelstenen apart, want ze vormen jouw score voor deze beurt.</p>
      <p style={p}>Nu komt het zenuwslopende deel: je mag doorgaan met gooien met de overgebleven dobbelstenen. Bij elke volgende worp moet je weer dobbelstenen apart leggen, maar let op &ndash; je moet steeds een ANDERE waarde kiezen dan wat je al apart hebt gelegd. Regenwormen tellen als hun eigen categorie, dus zelfs als je al regenwormen apart hebt gelegd, kun je nog steeds een 1, 2, 3, 4 of 5 kiezen.</p>
      <p style={p}>Na elke worp sta je voor een hartverscheurende beslissing: doorgaan of stoppen? Als je stopt, tel je de waarden van alle apart gelegde dobbelstenen bij elkaar op. Regenwormen tellen stuk voor stuk als 5 punten. Met deze totaalscore kun je een regenwormtegel uit het midden pakken waarvan de waarde overeenkomt met jouw score, OF je kunt een tegel van een tegenstander stelen, als die de exacte waarde heeft die jij net gooide.</p>
      <p style={p}>Maar pas op! Als je na een worp geen nieuwe waarde apart kunt leggen, heb je jezelf klemgezet! Je verliest je beurt &eacute;n de bovenste tegel van jouw stapel, die je beschaamd moet terugleggen naar het midden van de tafel. Zo pijnlijk &hellip;</p>

      <h2 style={h2}>Wanneer de wormen opraken</h2>
      <p style={p}>Het spel gaat door tot alle tegels uit het midden zijn gepakt. Op dat moment telt iedereen het aantal regenwormen op hun verzamelde tegels. De tegels hebben elk een verschillend aantal wormen (van 1 tot 4), dus het is niet alleen de hoeveelheid tegels die telt, maar vooral welke tegels je hebt verzameld. De speler met de meeste regenwormen is de ultieme Wormenkoning(in) en wint het spel!</p>

      <h2 style={h2}>Regenwormtactieken voor Strategische Slimmeriken</h2>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>
        {[
          'Wees niet te gulzig! Vaak is het beter om met een lagere score te stoppen en een tegel te pakken dan door te blijven gooien en alles te verliezen.',
          'Houd je tegenstanders in de gaten! Als je weet dat iemand een tegel met waarde 25 heeft, kun je proberen om precies 25 te gooien en die tegel te stelen.',
          'De regenwormdobbelstenen zijn sleutel tot hoge scores. Elke regenworm telt als 5 punten, dus drie regenwormen alleen al geven je 15 punten!',
          'Begin het spel met lagere tegels. De tegels met lagere waarden hebben soms meer regenwormen, en aan het einde van het spel gaat het om de wormen, niet om de getallen!',
          'Klaar om de aarde om te wroeten en te graven naar glorie? Grijp die dobbelstenen, leg de tegels klaar en ervaar de zinderende spanning van Regenwormen.',
        ].map((text, i) => (
          <li key={i} style={{ ...p, padding: '14px 16px', background: '#f4f0e6', border: '1px solid #ded7c5', borderRadius: 2 }}>{text}</li>
        ))}
      </ul>
    </section>
  )
}
```

- [ ] **Step 2: Write the Leaderboard page**

```jsx
// frontend/src/pages/Leaderboard.jsx
import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function Leaderboard() {
  const [rows, setRows] = useState([])
  useEffect(() => { api.leaderboard().then(setRows).catch(() => setRows([])) }, [])

  return (
    <section style={{ maxWidth: 720, margin: '0 auto', padding: '44px 20px 70px', width: '100%' }}>
      <h1 style={{ fontWeight: 900, fontSize: 'clamp(28px, 5vw, 42px)', margin: '0 0 6px', color: '#16150f' }}>Leaderboard</h1>
      <p style={{ fontSize: 15, color: '#6d6961', margin: '0 0 26px' }}>Worms collected this season.</p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {rows.map(row => (
          <div key={row.rank} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '13px 16px', borderRadius: 2, background: '#f4f0e6', border: '1px solid #ded7c5' }}>
            <span style={{ fontWeight: 900, fontSize: 15, color: '#a8232b', width: 26 }}>{row.rank}</span>
            <span style={{ flex: '1 1 auto', fontWeight: 700, fontSize: 15, color: '#1c1a14' }}>{row.name}</span>
            <span style={{ fontSize: 13, color: '#6d6961' }}>{row.games} games</span>
            <span style={{ fontWeight: 900, fontSize: 15, color: '#a8232b', width: 46, textAlign: 'right' }}>{row.worms}</span>
          </div>
        ))}
        {rows.length === 0 && <p style={{ color: '#6d6961', fontSize: 14 }}>No games played yet — be the first to claim a tile.</p>}
      </div>
    </section>
  )
}
```

- [ ] **Step 3: Write the Profile page**

```jsx
// frontend/src/pages/Profile.jsx
import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

export default function Profile() {
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  useEffect(() => { api.profile().then(setStats).catch(() => setStats(null)) }, [])

  const initials = (user?.display_name || '?').slice(0, 2).toUpperCase()
  const cards = stats ? [
    { value: stats.games, label: 'Games played' },
    { value: stats.worms, label: 'Worms won' },
    { value: `${stats.win_rate}%`, label: 'Win rate' },
    { value: stats.best_turn, label: 'Best single turn' },
  ] : []

  return (
    <section style={{ maxWidth: 720, margin: '0 auto', padding: '44px 20px 70px', width: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 18, marginBottom: 30 }}>
        <span style={{ width: 64, height: 64, borderRadius: 999, background: '#a8232b', color: '#fff', display: 'grid', placeItems: 'center', fontWeight: 900, fontSize: 22 }}>{initials}</span>
        <div>
          <h1 style={{ fontWeight: 900, fontSize: 30, margin: 0, color: '#16150f' }}>{user?.display_name}</h1>
          <div style={{ fontSize: 14, color: '#6d6961' }}>{user?.email}</div>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12 }}>
        {cards.map(c => (
          <div key={c.label} style={{ padding: 18, borderRadius: 2, background: '#f4f0e6', border: '1px solid #ded7c5' }}>
            <div style={{ fontWeight: 900, fontSize: 28, color: '#a8232b' }}>{c.value}</div>
            <div style={{ fontSize: 12, letterSpacing: '.1em', textTransform: 'uppercase', color: '#6d6961', marginTop: 4 }}>{c.label}</div>
          </div>
        ))}
      </div>
    </section>
  )
}
```

- [ ] **Step 4: Verify the leaderboard API contract with curl**

Run: `docker compose up -d --build && sleep 20 && curl -s http://localhost:5173/api/leaderboard`
Expected: `[]` (empty JSON array, no games played yet)

- [ ] **Step 5: Manual verification**

Play a full bot game to completion (per Task 15's check). Then in the browser: visit `/leaderboard` and confirm your name and worm count appear; visit `/profile` and confirm "Games played", "Worms won", "Win rate" and "Best single turn" all reflect that game. Visit `/rules` and confirm the full Dutch copy renders with the hero image.

Run: `docker compose down`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Rules.jsx frontend/src/pages/Leaderboard.jsx frontend/src/pages/Profile.jsx
git commit -m "feat: wire Rules, Leaderboard, and Profile pages"
```

---

## Task 17: Live PvP in the frontend

**Files:**
- Modify: `frontend/src/pages/Lobby.jsx` (cancel-match support)
- Modify: `frontend/src/pages/Table.jsx` (no game logic changes needed — it already renders whatever `game_state`/`player*_name` it receives; this task is about matchmaking UX)

**Interfaces:**
- Consumes: `match_found`/`game_state` events already emitted by the backend (Task 11) and already handled generically by `Table.jsx` (Task 15) and `Lobby.jsx` (Task 14).

- [ ] **Step 1: Add a cancel button to the matchmaking indicator**

```jsx
// frontend/src/pages/Lobby.jsx — replace the matchmaking block:
        {matchmaking && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 20, fontWeight: 600, fontSize: 13, color: '#a8232b' }}>
            <span style={{ width: 15, height: 15, border: '2px solid #b3ab99', borderTopColor: '#a8232b', borderRadius: 999, display: 'inline-block', animation: 'rw-spin .8s linear infinite' }} />
            Looking for an opponent
            <button onClick={() => { socket.emit('cancel_match'); setMatchmaking(false) }} style={{ background: 'none', border: 0, color: '#6d6961', textDecoration: 'underline', cursor: 'pointer', font: "600 13px 'Archivo', sans-serif" }}>
              Cancel
            </button>
          </div>
        )}
```

- [ ] **Step 2: Manual verification — two-browser PvP**

`docker compose up -d --build`. Open two separate browser sessions (e.g., one normal window, one private/incognito window) at `http://localhost:5173/`. Sign up as two different users. In both, click "Find an opponent" — the first shows the spinner, the second immediately transitions both into `/table` on the same game. Verify: turn order alternates correctly between the two real users (not a bot), each can only act on their own turn, dice/log/tile state stays in sync between both browser windows after every action, and playing to completion shows the correct winner in both windows. Then start a second PvP game and close one browser tab mid-game — verify the other player sees the game auto-resign in their favor after ~30 seconds (the disconnect grace period).

Run: `docker compose down`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Lobby.jsx
git commit -m "feat: add cancel-match control for live PvP matchmaking"
```

---

## Final verification

- [ ] Run the full backend suite one more time: `cd backend && python -m pytest -v` — expect all tests passing.
- [ ] Run `docker compose up -d --build` from the repo root and confirm all three containers report healthy/running: `docker compose ps`.
- [ ] Walk through the manual checklist end-to-end one more time: sign up → play bot game to completion → leaderboard/profile update → sign in as a second user in another browser → PvP match → resign and disconnect-grace paths.
- [ ] `docker compose down`
