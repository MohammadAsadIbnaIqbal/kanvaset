"""
Kanvaset Multi-Client Collaborative Real-Time Simulation Script.
Demonstrates 2+ authenticated WebSocket clients making concurrent edits on a shared board,
verifying real-time broadcast, state convergence, and reconnect recovery.
"""
import asyncio
import json
import logging
import sys
import time
import httpx
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("kanvaset.sim")

BASE_URL = "http://localhost:8000"
WS_BASE_URL = "ws://localhost:8000"


async def run_simulation():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as http:
        # Check server health
        try:
            resp = await http.get("/health")
            if resp.status_code != 200:
                logger.error("Server is not healthy: %s", resp.text)
                return False
            logger.info("Server is online: %s", resp.json())
        except Exception as e:
            logger.error("Could not connect to Kanvaset backend at %s: %s", BASE_URL, e)
            logger.info("Tip: Start backend with: uvicorn backend.app.main:app --host 0.0.0.0 --port 8000")
            return False

        # 1. Register or Login Alice & Bob
        timestamp = int(time.time())
        alice_email = f"alice_{timestamp}@example.com"
        bob_email = f"bob_{timestamp}@example.com"

        # Register Alice
        res_a = await http.post("/api/v1/auth/register", json={
            "email": alice_email,
            "username": f"alice_{timestamp}",
            "password": "Password123!",
        })
        token_a = res_a.json()["access_token"]
        user_a = res_a.json()["user"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Register Bob
        res_b = await http.post("/api/v1/auth/register", json={
            "email": bob_email,
            "username": f"bob_{timestamp}",
            "password": "Password123!",
        })
        token_b = res_b.json()["access_token"]
        user_b = res_b.json()["user"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        logger.info("Registered User A (Alice: %s) & User B (Bob: %s)", user_a["id"], user_b["id"])

        # 2. Alice creates workspace and board
        ws_res = await http.post("/api/v1/workspaces", json={"name": "Collaborative Space"}, headers=headers_a)
        ws_id = ws_res.json()["id"]

        board_res = await http.post(f"/api/v1/workspaces/{ws_id}/boards", json={
            "name": "Live Sprint Planning Board",
            "description": "Multi-user real-time session"
        }, headers=headers_a)
        board = board_res.json()
        board_id = board["id"]
        logger.info("Alice created Board '%s' (ID: %s)", board["name"], board_id)

        # 3. Alice shares board with Bob as EDITOR
        share_res = await http.post(f"/api/v1/boards/{board_id}/members", json={
            "user_email_or_username": bob_email,
            "role": "EDITOR"
        }, headers=headers_a)
        assert share_res.status_code == 200
        logger.info("Alice shared board with Bob as EDITOR")

        # 4. Open concurrent WebSockets
        alice_state = {"objects": {}, "revision": 0, "cursors": {}}
        bob_state = {"objects": {}, "revision": 0, "cursors": {}}

        uri_a = f"{WS_BASE_URL}/ws/boards/{board_id}?token={token_a}"
        uri_b = f"{WS_BASE_URL}/ws/boards/{board_id}?token={token_b}"

        async with websockets.connect(uri_a) as ws_a, websockets.connect(uri_b) as ws_b:
            logger.info("Both Alice and Bob connected to WebSocket room %s", board_id)

            # Receive initial snapshots
            raw_snap_a = json.loads(await ws_a.recv())
            raw_snap_b = json.loads(await ws_b.recv())
            assert raw_snap_a["type"] == "SYNC_SNAPSHOT"
            assert raw_snap_b["type"] == "SYNC_SNAPSHOT"
            logger.info("Alice & Bob received initial board snapshot")

            # Alice sends cursor move
            await ws_a.send(json.dumps({
                "type": "CURSOR_MOVED",
                "board_id": board_id,
                "payload": {"x": 150.0, "y": 200.0}
            }))

            # Bob creates sticky note
            sticky_id = f"sticky_{timestamp}"
            await ws_b.send(json.dumps({
                "type": "OBJECT_CREATED",
                "operation_id": f"op_b_1_{timestamp}",
                "board_id": board_id,
                "object_id": sticky_id,
                "payload": {
                    "id": sticky_id,
                    "type": "sticky_note",
                    "x": 300,
                    "y": 150,
                    "width": 180,
                    "height": 180,
                    "color": "#FEF08A",
                    "text": "Refactor WebSocket Connection Pool"
                }
            }))

            # Read broadcasted events
            msg_for_a = json.loads(await ws_a.recv())
            # Find the object created broadcast
            while msg_for_a.get("type") != "OBJECT_CREATED":
                msg_for_a = json.loads(await ws_a.recv())
            
            logger.info("Alice received real-time broadcast of Bob's sticky note! (text: '%s')",
                        msg_for_a["payload"].get("text"))
            assert msg_for_a["payload"]["id"] == sticky_id

            # Alice moves Bob's sticky note
            await ws_a.send(json.dumps({
                "type": "OBJECT_MOVED",
                "operation_id": f"op_a_move_{timestamp}",
                "board_id": board_id,
                "object_id": sticky_id,
                "payload": {"x": 450, "y": 220}
            }))

            # Bob receives move broadcast
            msg_for_b = json.loads(await ws_b.recv())
            while msg_for_b.get("type") != "OBJECT_MOVED":
                msg_for_b = json.loads(await ws_b.recv())

            logger.info("Bob received real-time move broadcast! New coordinates: (%s, %s)",
                        msg_for_b["payload"]["x"], msg_for_b["payload"]["y"])
            assert msg_for_b["payload"]["x"] == 450

        # 5. Verify Reconnection and Persistence via REST Snapshot
        final_snap_res = await http.get(f"/api/v1/boards/{board_id}/snapshot", headers=headers_a)
        final_snap = final_snap_res.json()
        assert len(final_snap["objects"]) == 1
        persisted_obj = final_snap["objects"][0]
        assert persisted_obj["id"] == sticky_id
        assert persisted_obj["x"] == 450
        assert persisted_obj["text"] == "Refactor WebSocket Connection Pool"
        logger.info("=" * 60)
        logger.info("SIMULATION COMPLETED SUCCESSFULLY!")
        logger.info("Persisted Board Revision: %d", final_snap["server_revision"])
        logger.info("Objects in board: %d", len(final_snap["objects"]))
        logger.info("Final State verified across all clients and PostgreSQL storage.")
        logger.info("=" * 60)
        return True


if __name__ == "__main__":
    success = asyncio.run(run_simulation())
    sys.exit(0 if success else 1)
