# Kanvaset — Technical Architecture & Engineering Design

This document details the architectural design, synchronization model, concurrency handling, and system topology of **Kanvaset**, a production-grade real-time collaborative workspace.

---

## 1. High-Level System Architecture

```mermaid
flowchart TD
    subgraph Clients["Browser Clients (React 19 + TypeScript)"]
        UserA["User A (Owner)"]
        UserB["User B (Editor)"]
        UserC["User C (Viewer)"]
    end

    subgraph Gateway["Reverse Proxy (Nginx)"]
        Proxy["Nginx Port 3000 / 80<br/>- Static SPA Serving<br/>- REST Proxy: /api/*<br/>- WS Upgrade: /ws/*"]
    end

    subgraph BackendCluster["FastAPI Backend Cluster"]
        Node1["FastAPI Worker 1<br/>- REST API<br/>- Board Connection Manager<br/>- Collaboration Engine"]
        Node2["FastAPI Worker 2<br/>- REST API<br/>- Board Connection Manager<br/>- Collaboration Engine"]
    end

    subgraph EventBus["Pub/Sub & Cache (Redis 7)"]
        PubSub["Redis Pub/Sub (`board:{id}:events`)<br/>- Active Presence Sets<br/>- Operation Deduplication Cache"]
    end

    subgraph Storage["Persistent Storage (PostgreSQL 16)"]
        DB[("PostgreSQL Database<br/>- Users & Workspaces<br/>- Boards & Members (RBAC)<br/>- BoardObjects (State)<br/>- BoardOperations (Audit Trail)")]
    end

    UserA <-->|HTTP / WebSocket| Proxy
    UserB <-->|HTTP / WebSocket| Proxy
    UserC <-->|HTTP / WebSocket| Proxy

    Proxy <--> Node1
    Proxy <--> Node2

    Node1 <--> PubSub
    Node2 <--> PubSub

    Node1 <--> DB
    Node2 <--> DB
```

---

## 2. Real-Time Synchronization Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor Client as Browser Client
    participant Server as FastAPI WebSocket Handler
    participant Redis as Redis Pub/Sub & Presence
    participant DB as PostgreSQL Database

    Client->>Server: Connect: /ws/boards/{id}?token={jwt}
    Server->>Server: Validate JWT and Board RBAC Role
    alt Lacks Permission or Invalid Token
        Server-->>Client: Close WebSocket (Policy Violation 1008)
    else Authorized
        Server->>Server: Register local socket connection
        Server->>Redis: Set presence in presence:{board_id}
        Server->>Redis: Publish USER_JOINED event
        Server->>DB: Query current board snapshot & active objects
        DB-->>Server: Board revision & objects
        Server-->>Client: Send SYNC_SNAPSHOT message
    end

    loop Active Collaborative Session
        Client->>Server: Send Semantic Operation (e.g. OBJECT_MOVED)
        Server->>Server: Check role: reject if VIEWER
        Server->>Redis: Check operation_id deduplication
        Server->>DB: Increment board revision & object version, persist mutation
        DB-->>Server: Commit success
        Server->>Redis: Publish OBJECT_MOVED to board:{id}:events
        Redis-->>Server: Broadcast event to all cluster nodes
        Server-->>Client: Send ACK (revision: N)
        Server-->>Client: Broadcast OBJECT_MOVED to room participants
    end

    Client->>Server: Disconnect / Tab Close
    Server->>Redis: Remove user from presence
    Server->>Redis: Publish USER_LEFT event
    Server->>Server: Clean up connection manager
```

---

## 3. Concurrency Model & Conflict Resolution

### Semantic Operations vs Whole-Board Diffs
Instead of serializing the entire board on every cursor flick or pixel drag, Kanvaset uses **semantic operation messages**:
- `OBJECT_CREATED`
- `OBJECT_MOVED`
- `OBJECT_RESIZED`
- `OBJECT_UPDATED`
- `OBJECT_DELETED`
- `CURSOR_MOVED` (ephemeral)

### Ordering and Versioning
1. **Monotonic Board Revision (`revision`)**:
   Every mutation operation increments the board's monotonic revision counter by 1 in an atomic database transaction. This provides an absolute total order for all board modifications.
2. **Object Versioning (`version`)**:
   Every `BoardObject` carries an integer `version` field starting at 1 and incremented upon each accepted mutation.
3. **Idempotency & Deduplication (`operation_id`)**:
   Every client operation generates a unique `operation_id` (`op_<timestamp>_<random>`). Before processing, the server checks Redis or memory LRU cache. Network retries or replayed messages are safely de-duplicated without re-applying state changes.
4. **Resynchronization (`SYNC_REQUEST`)**:
   If a client detects a revision gap (`client_revision < server_revision - 1`) or reconnects after temporary network loss, it issues a `SYNC_REQUEST`. The server responds with an authoritative `SYNC_SNAPSHOT`.

---

## 4. Role-Based Access Control (RBAC)

Kanvaset enforces authorization on every REST request and WebSocket connection:
- **`OWNER`**: Full administrative control. Can rename or delete board, invite members, and change permissions.
- **`EDITOR`**: Can create, move, resize, update, and delete objects on the board. Can view presence and cursors.
- **`VIEWER`**: Read-only access. Can view real-time changes, presence, and cursors. Any mutation operations sent by a viewer are rejected with an explicit `ERROR` envelope.

---

## 5. Horizontal Scaling with Redis

- **Local Broker vs Distributed Broker**:
  In single-node or testing environments, `backend/app/core/redis.py` automatically activates an asynchronous in-memory broker (`InMemoryEventBroker`).
- In multi-instance Docker or Kubernetes environments, Redis Pub/Sub coordinates events between all backend workers on channel `board:{board_id}:events`. When Worker 1 commits an operation, it publishes to Redis, and Worker 2 receives it and broadcasts to its locally connected WebSockets.
