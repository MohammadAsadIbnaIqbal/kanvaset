# Kanvaset — Real-Time Collaborative Workspace

![CI Pipeline](https://github.com/MohammadAsadIbnaIqbal/kanvaset/actions/workflows/ci.yml/badge.svg)
![Python Version](https://img.shields.io/badge/python-3.12%20%7C%203.14-blue)
![FastAPI](https://img.shields.io/badge/backend-FastAPI%20%2B%20WebSockets-009688)
![React](https://img.shields.io/badge/frontend-React%2019%20%2B%20TypeScript-61DAFB)
![PostgreSQL](https://img.shields.io/badge/database-PostgreSQL%2016-336791)
![Redis](https://img.shields.io/badge/pubsub-Redis%207-DC382D)
![Docker](https://img.shields.io/badge/deployment-Docker%20Compose-2496ED)

**Kanvaset** is a production-oriented multi-user collaborative workspace and whiteboard. Multiple authenticated users can work on the same board simultaneously, creating, moving, editing, and deleting objects in near real time via WebSockets.

---

## Key Highlights & Engineering Features

- **Semantic WebSocket Synchronization**: Instead of sending heavy full-board snapshots on every interaction, Kanvaset transmits typed semantic operations (`OBJECT_CREATED`, `OBJECT_MOVED`, `OBJECT_RESIZED`, `OBJECT_UPDATED`, `OBJECT_DELETED`, `CURSOR_MOVED`).
- **Deterministic Concurrency & Conflict Handling**:
  - Monotonic board `revision` numbers guarantee strict global ordering.
  - Per-object `version` tracking resolves concurrent modifications with deterministic ordering.
  - `operation_id` deduplication prevents duplicate mutations across network retries.
- **Multi-User Presence & Ephemeral Cursors**:
  - Displays currently connected participants with color-coded avatar pills.
  - Throttled real-time mouse cursor streaming with low overhead.
  - Automatic disconnect cleanup and reconnect state recovery.
- **Granular Role-Based Access Control (RBAC)**:
  - Board-level permissions: **OWNER**, **EDITOR**, **VIEWER**.
  - Server-side enforcement across all REST endpoints and WebSocket frames (mutation attempts by Viewers are rejected with typed error envelopes).
- **Horizontal Scalability with Redis Pub/Sub**:
  - Broadcasts board events across multi-instance backend clusters via Redis Pub/Sub.
  - Built-in asynchronous in-memory event broker fallback for standalone development and zero-dependency unit tests.
- **Production-Grade Infrastructure**:
  - Multi-stage Dockerfiles for backend and frontend.
  - Nginx reverse proxy with native WebSocket protocol upgrades.
  - PostgreSQL 16 persistence with automated Alembic database migrations.
  - GitHub Actions CI pipeline running tests and static analysis on every push.

---

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | React 19, TypeScript, Tailwind CSS v4, Lucide | Interactive whiteboard UI, transform controls, live cursors |
| **Backend** | Python 3.12+, FastAPI, WebSockets | Asynchronous REST API, connection management, concurrency engine |
| **Database** | PostgreSQL 16, SQLAlchemy 2.0 (async), Alembic | Relational data persistence, transactional schema migrations |
| **Pub/Sub & Cache** | Redis 7 (with InMemoryEventBroker fallback) | Multi-node event broadcasting, active presence tracking |
| **Reverse Proxy** | Nginx Alpine | Static asset delivery, SPA routing, SSL/WebSocket proxying |
| **Deployment** | Docker & Docker Compose | Containerized reproducible multi-service topology |

---

## Quickstart with Docker Compose

Ensure Docker is installed, then run:

```bash
# 1. Clone repository
git clone https://github.com/MohammadAsadIbnaIqbal/kanvaset.git
cd kanvaset

# 2. Launch all services (PostgreSQL, Redis, Backend, Frontend)
docker compose up --build -d

# 3. Access Kanvaset in your browser:
# Frontend App: http://localhost:3000
# Backend API Docs: http://localhost:8000/docs
# Health Probe: http://localhost:8000/health
```

To stop all services:
```bash
docker compose down
```

---

## Local Development Setup

### 1. Backend Setup

```bash
# From repository root
cd backend

# Install dependencies
pip install -r requirements.txt

# Run migrations (SQLite for quick local dev or PostgreSQL)
alembic upgrade head

# Start FastAPI server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup

```bash
cd frontend

# Install npm dependencies
npm install

# Start Vite development server (proxies /api and /ws to http://localhost:8000)
npm run dev
```

Visit `http://localhost:5173` to open the local development interface.

---

## Running the Automated Test Suite

### 1. Backend Unit, Concurrency, and WebSocket Tests

```bash
pytest backend/tests -v --cov=backend/app
```

All tests execute against async SQLite and the in-memory broker with zero external dependencies required.

### 2. Frontend Typecheck and Production Build

```bash
cd frontend
npm run build
```

### 3. Multi-Client Concurrency & Persistence Simulation

To run an automated end-to-end integration test simulating multiple concurrent WebSocket clients modifying board objects simultaneously:

```bash
python scripts/simulate_collaboration.py
```

---

## WebSocket Protocol Specification

Clients connect to:
`ws://localhost:8000/ws/boards/{board_id}?token={jwt_token}`

### Typed Message Envelope

```json
{
  "type": "OBJECT_MOVED",
  "board_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "operation_id": "op_1726123456_a9b8c7",
  "object_id": "sticky_101",
  "payload": {
    "id": "sticky_101",
    "x": 350.0,
    "y": 220.0
  },
  "client_revision": 4,
  "server_revision": 5,
  "timestamp": 1726123456.789
}
```

### Supported Operation Types

| Message Type | Direction | Description |
|---|---|---|
| `SYNC_SNAPSHOT` | Server &rarr; Client | Sent immediately on connect or recovery. Contains board objects, presence, and role. |
| `OBJECT_CREATED` | Bidirectional | Creates a new sticky note, shape, text box, or connector. |
| `OBJECT_MOVED` | Bidirectional | Updates position coordinates `(x, y)` of an object. |
| `OBJECT_RESIZED` | Bidirectional | Updates width, height, and coordinates of an object. |
| `OBJECT_UPDATED` | Bidirectional | Updates content text, color, stroke, or custom properties. |
| `OBJECT_DELETED` | Bidirectional | Soft-deletes an object from the active canvas. |
| `CURSOR_MOVED` | Bidirectional | Ephemeral live mouse coordinates `(x, y)` streamed to participants. |
| `USER_JOINED` | Server &rarr; Client | Broadcasted when a new authenticated user joins the board. |
| `USER_LEFT` | Server &rarr; Client | Broadcasted when a participant disconnects. |
| `SYNC_REQUEST` | Client &rarr; Server | Dispatched when a client requests full resynchronization. |
| `ACK` | Server &rarr; Client | Confirms operation acceptance and includes current server revision. |
| `ERROR` | Server &rarr; Client | Returned when an unauthorized operation or validation failure occurs. |

---

## Project Structure

```
kanvaset/
├── .github/
│   └── workflows/
│       └── ci.yml                 # GitHub Actions CI pipeline
├── backend/
│   ├── alembic/                   # Alembic database migrations
│   │   ├── versions/              # Migration scripts
│   │   └── env.py
│   ├── app/
│   │   ├── api/                   # REST and WebSocket route handlers
│   │   │   └── v1/
│   │   │       ├── auth.py
│   │   │       ├── boards.py
│   │   │       ├── workspaces.py
│   │   │       └── ws.py
│   │   ├── core/                  # Config, Database, Redis, and Security
│   │   ├── models/                # SQLAlchemy ORM models
│   │   ├── schemas/               # Pydantic validation schemas
│   │   ├── services/              # Auth, Workspace, Board, and Collaboration engines
│   │   └── main.py                # FastAPI entrypoint
│   ├── tests/                     # Automated pytest suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Auth/              # Login and Register views
│   │   │   ├── Board/             # Interactive Canvas, Toolbar, Header, ShareModal
│   │   │   ├── Dashboard/         # Workspaces and Boards management
│   │   │   └── Navbar.tsx
│   │   ├── context/               # Global AuthContext
│   │   ├── hooks/                 # Real-time WebSocket hook with reconnect logic
│   │   ├── services/              # REST API client
│   │   └── types/                 # TypeScript interfaces
│   ├── Dockerfile
│   ├── nginx.conf                 # Nginx proxy and SPA routing
│   ├── package.json
│   └── vite.config.ts
├── scripts/
│   └── simulate_collaboration.py  # Real-time multi-client simulation script
├── ARCHITECTURE.md                # Detailed technical architecture design
├── docker-compose.yml             # Container orchestration
├── pytest.ini                     # Pytest asyncio configuration
├── .gitignore
└── README.md
```

---

## License

MIT License. Designed and built for portfolio and production engineering demonstration.
