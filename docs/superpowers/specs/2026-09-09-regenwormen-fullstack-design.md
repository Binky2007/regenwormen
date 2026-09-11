# Regenwormen — full-stack design

Date: 2026-09-09
Status: Approved for implementation planning

## 1. Purpose

Turn the existing Regenwormen prototype (a single self-contained React-ish
component with all state client-side and no persistence — see
`Regenwormen.dc.html` imported from the Claude Design project) into a real
full-stack app:

- React frontend (Vite)
- Python/Flask backend
- MySQL database
- Real email/password auth
- A server-authoritative game engine shared by bot games and live PvP
- Real-time matchmaking and live two-player games (Socket.IO)
- A dev-friendly Docker Compose environment

The visual design (screens, colors, layout, copy) from the prototype is the
source of truth for the frontend UI and is preserved as-is; only the
underlying wiring changes (real data, real auth, real game engine).

## 2. Screens (from the existing design)

- **Lobby** — hero, "Play the bot" / "Find an opponent" (now real matchmaking)
- **Table** — the game board: seats, center tiles, dice roll, set-aside pile,
  turn log, resign
- **Rules** — static rules content, unchanged
- **Leaderboard** — now backed by real aggregated data
- **Profile** — now backed by real aggregated data for the signed-in user
- **Signed out** — sign-in prompt

## 3. Architecture

```
regenwormpje/
├── docker-compose.yml
├── .env
├── mysql/
│   └── init/001_schema.sql
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                  # app factory + socketio.run entrypoint
│   ├── config.py
│   ├── extensions.py           # db, jwt, socketio singletons
│   ├── models.py               # SQLAlchemy models
│   ├── auth/
│   │   ├── routes.py           # /api/auth/*
│   │   └── security.py
│   ├── stats/
│   │   └── routes.py           # /api/leaderboard, /api/profile
│   ├── game/
│   │   ├── engine.py           # pure game state machine (ported from JS)
│   │   ├── bot.py              # bot move selection
│   │   ├── manager.py          # in-memory active-game registry, persistence
│   │   ├── matchmaking.py      # in-memory queue
│   │   └── socket_handlers.py  # Socket.IO event handlers, /game namespace
│   └── tests/
│       ├── test_engine.py
│       └── test_auth.py
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.js          # dev server proxy to backend
    └── src/
        ├── main.jsx / App.jsx (router)
        ├── context/AuthContext.jsx
        ├── context/SocketContext.jsx
        ├── api/client.js       # fetch wrapper, attaches JWT
        └── pages/
            ├── Lobby.jsx, Table.jsx, Rules.jsx,
            ├── Leaderboard.jsx, Profile.jsx, SignedOut.jsx
```

Frontend talks to the backend two ways:
- **REST** (`/api/...`) for auth, leaderboard, profile — simple request/response.
- **Socket.IO** (`/game` namespace) for anything game-state related — bot
  games, matchmaking, live PvP. One transport for both game modes keeps the
  client code (and the server's game engine) unified.

In dev, the Vite dev server proxies `/api` and `/socket.io` to the backend
container so the browser only ever talks to one origin.

## 4. Data model (MySQL)

```sql
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
  player1_id    INT NOT NULL REFERENCES users(id),
  player2_id    INT NULL REFERENCES users(id),   -- NULL for bot games
  status        ENUM('active','finished','resigned') NOT NULL DEFAULT 'active',
  state_json    JSON NOT NULL,                    -- full engine state snapshot
  winner        ENUM('player1','player2','draw') NULL,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at   DATETIME NULL
);

CREATE TABLE game_results (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  game_id         INT NOT NULL REFERENCES games(id),
  user_id         INT NOT NULL REFERENCES users(id),
  worms           INT NOT NULL,
  tiles_won       JSON NOT NULL,     -- e.g. [24, 31, 22]
  is_winner       BOOLEAN NOT NULL,
  best_turn_score INT NOT NULL,      -- highest claimed-tile score this player hit in this game
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Leaderboard = `SUM(worms)`/`COUNT(*)` from `game_results` grouped by user,
ordered by worms desc. Profile = same, filtered to the signed-in user, plus
`MAX(best_turn_score)` for the "best single turn" stat. The engine tracks
the score of every successful claim during a game (it already computes this
value to decide claim eligibility) and the manager records the max when it
writes the `game_results` row at game end.

`state_json` persists the full engine state after every action so an active
game survives a backend restart and a reconnecting client can resume.

## 5. Game engine (backend/game/engine.py)

A faithful Python port of the JS state machine already in the design
(`freshGame`, `rollInto`, `pickInto`, `bustInto`, `claimInto`, `endTurn`,
scoring, `options`/claim eligibility, bot value heuristic). This is the
single source of truth; the frontend does no game math, only rendering.

State shape (mirrors the JS `state`):
```python
{
  "center": [21..36],       # tiles still available
  "out": [...],             # tiles removed from play
  "stacks": [[...], [...]], # player1's / player2's claimed tiles, in order
  "turn": 0 | 1,
  "roll": [...],            # current unresolved roll (values 1-5 or "w")
  "aside": [...],           # dice set aside this turn
  "log": [...],
  "result": null | {"winner": ..., "worms": [n, n]}
}
```

Actions (validated server-side before mutating state):
- `roll` — only when it's your turn and you have dice left to roll
- `pick(face)` — only a face present in the current roll and not already used
  this turn
- `claim` / `stop` — only when a valid take/steal option exists
- `resign` — ends the game as a loss for the resigning player

Bot moves are computed by `game/bot.py` (ports the existing `botValue`
heuristic) and run as background Socket.IO tasks with the same timing
choreography as the current `setTimeout`-based JS (`botSpeed`), emitting
`game_state` updates as it goes so the frontend animation beats are
unaffected.

## 6. Auth

REST, under `/api/auth`:
- `POST /signup` `{email, password, display_name}` → creates user, returns JWT
- `POST /login` `{email, password}` → returns JWT
- `GET /me` (JWT required) → current user profile

Passwords hashed with `werkzeug.security.generate_password_hash`. JWT via
`flask-jwt-extended`, short-lived access token, stored in the frontend in
memory + `localStorage` and sent as `Authorization: Bearer <token>` on REST
calls and as an auth payload on the Socket.IO `connect` handshake (server
verifies it in the `connect` handler and rejects unauthenticated sockets).

## 7. Real-time gameplay & matchmaking (Socket.IO, `/game` namespace)

Client → server events:
- `start_bot_game` — creates a `mode='bot'` game, joins room `game:<id>`
- `find_match` — enters the in-memory matchmaking queue
- `cancel_match` — leaves the queue
- `action` `{type: 'roll'|'pick'|'claim'|'stop'|'resign', payload}`

Server → client events:
- `match_found` `{game_id, opponent}`
- `game_state` `{...full state...}` — sent after every accepted action, to
  the whole room
- `error` `{message}` — rejected/illegal action

Matchmaking: a simple in-memory FIFO queue of waiting `(user_id, sid)` pairs
inside the Flask-SocketIO process. When a second player joins, both are
dequeued, a `games` row is created (`mode='pvp'`), both sockets join
`game:<id>`, and both receive `match_found` then `game_state`. This is
process-local by design (single backend container in this dev setup) — it's
called out explicitly as not horizontally-scalable, which is fine for this
project's scope.

Disconnect handling (v1, per your confirmation): if a player in an active
PvP game disconnects, start a short grace timer (e.g. 30s); if they haven't
reconnected (same user_id, new socket, rejoining `game:<id>`) when it fires,
auto-resign them and finish the game. Reconnect-and-resume within the grace
window is included since it's cheap; anything fancier (spectating,
multi-device sync) is out of scope.

## 8. REST API summary

| Method | Path                | Auth | Purpose |
|--------|---------------------|------|---------|
| POST   | /api/auth/signup    | no   | create account |
| POST   | /api/auth/login     | no   | issue JWT |
| GET    | /api/auth/me        | yes  | current user |
| GET    | /api/leaderboard    | no   | aggregated worms per user, ranked |
| GET    | /api/profile        | yes  | signed-in user's aggregated stats |

## 9. Frontend

Vite + React, `react-router-dom` for the six views, functional
components/hooks. Visual styling ported faithfully from the `.dc.html`
(same inline style values, fonts, colors, layout) into JSX — no visual
redesign, just re-platforming.

- `AuthContext` — signup/login/logout, current user, token persistence
- `SocketContext` — opens the `/game` socket once authenticated, exposes
  `emit`/event subscriptions
- `Table.jsx` — subscribes to `game_state`, renders exactly the board the
  design specifies, dispatches `action` events from the existing button
  wiring (roll/pick/claim/stop/resign)
- `Leaderboard.jsx` / `Profile.jsx` — fetch from the REST endpoints instead
  of using hardcoded arrays

## 10. Docker (dev-friendly)

`docker-compose.yml` with three services on one network:
- `mysql` — `mysql:8`, named volume, schema loaded from `mysql/init/*.sql`
  on first boot
- `backend` — `python:3.12-slim`, `pip install -r requirements.txt`, source
  bind-mounted for hot reload, runs `python app.py`
  (`socketio.run(app, debug=True)` — eventlet-based, supports the Werkzeug
  reloader)
- `frontend` — `node:20`, source bind-mounted, `npm run dev -- --host`
  (Vite), dev server proxies `/api` and `/socket.io` to `backend:5000`

`.env` holds `MYSQL_ROOT_PASSWORD`, `MYSQL_DATABASE`, `MYSQL_USER`,
`MYSQL_PASSWORD`, `JWT_SECRET_KEY` — read by compose and by Flask config.

`docker compose up` brings up all three; frontend on `localhost:5173`,
backend on `localhost:5000`.

## 11. Testing strategy

- **Engine unit tests** (`backend/tests/test_engine.py`) — the game engine
  is pure/deterministic-enough (seed the RNG in tests) to unit test
  thoroughly: scoring, selectable faces, bust conditions, take/steal
  eligibility, end-of-game winner calc.
- **Auth tests** (`backend/tests/test_auth.py`) — signup/login/me against a
  test database (SQLite in-memory is fine for these, since the schema is
  simple enough not to need MySQL-specific features).
- **Manual end-to-end verification** — `docker compose up`, then in the
  browser: sign up, play a full bot game to completion, confirm the
  leaderboard/profile update; open two browser sessions, sign up as two
  users, use "Find an opponent" on both and play a live PvP game to
  completion including a resign path.

No frontend unit test suite is being added for this pass — verification is
manual-in-browser per the above, consistent with the size of the existing
prototype.

## 12. Implementation milestones

1. Docker Compose skeleton: MySQL + schema, Flask skeleton with a health
   endpoint, Vite skeleton — `docker compose up` shows the (static) lobby
   page end-to-end.
2. Auth: signup/login/me wired frontend-to-backend-to-MySQL.
3. Game engine: Python port + unit tests (no networking yet).
4. Socket.IO bot gameplay: engine wired into `/game` namespace for
   `start_bot_game`, Table.jsx fully functional against the bot, finished
   games persisted to `games`/`game_results`.
5. Leaderboard & Profile pages reading real aggregated data.
6. PvP: matchmaking queue, live two-player games, disconnect/resign
   handling.

## 13. Explicitly out of scope

- Horizontal scaling of matchmaking/socket state across multiple backend
  processes
- Spectating, chat, rematching the same opponent directly
- Password reset / email verification flows
- Mobile app / offline support
