# Regenwormen

A fan-made, browser-playable version of the dice game Regenwormen ("Rattle, Snake & Worms" / "Heckmeck"). Two players, eight dice, sixteen tiles: set dice aside, stop before you bust, and claim the tile that matches your score.

Play against a bot, or match up with another player online for a real-time PvP game over WebSockets.

## Stack

- **Backend**: Flask, Flask-SocketIO, Flask-SQLAlchemy, Flask-JWT-Extended, MySQL
- **Frontend**: React (Vite), react-router-dom, socket.io-client
- **Infra**: Docker Compose (mysql + backend + frontend)

## Getting started

Requires Docker and Docker Compose.

1. Copy the example environment file and adjust the secrets if you like:
   ```bash
   cp .env.example .env
   ```
2. Start everything:
   ```bash
   docker compose up -d --build
   ```
3. Open the app:
   - Frontend: http://localhost:5173
   - Backend API health check: http://localhost:5000/api/health

The frontend dev server proxies `/api` and `/socket.io` to the backend container, and both containers mount your local source for hot reload.

## Project structure

```
backend/
  app.py              Flask app factory, blueprint + Socket.IO wiring
  auth/                Registration / login (JWT)
  game/                Game engine, bot logic, matchmaking, socket handlers
  stats/               Leaderboard / profile stats endpoints
  tests/               pytest suite
frontend/
  src/pages/            Lobby, Table, Rules, Leaderboard, Profile, SignedOut
  src/context/           Auth / Socket / Game React contexts
  src/components/        Shared UI pieces
  src/lib/               Small client-side helpers (e.g. sound effects)
```

## Running tests

Backend tests run inside the backend container:

```bash
docker compose exec backend pytest
```

## Playing with friends

By default the app is only reachable on your own machine. To let someone outside your network join a match, expose your local frontend with a tunnel, e.g. [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/):

```bash
cloudflared tunnel --url http://localhost:5173
```

This prints a public `https://*.trycloudflare.com` URL you can share. Vite's dev server is configured with `allowedHosts: true` so it accepts requests coming through the tunnel's random hostname.
