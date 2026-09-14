import { useCallback, useEffect, useRef, useState } from "react";
import type { User } from "../types/auth";
import type { BoardObject, PresenceUser } from "../types/board";
import type { BoardSnapshotPayload, WSMessage } from "../types/ws";

export type ConnectionStatus = "connecting" | "connected" | "disconnected" | "reconnecting";

interface UseWebSocketBoardOptions {
  boardId: string;
  token: string | null;
  currentUser: User | null;
}

export function useWebSocketBoard({ boardId, token, currentUser }: UseWebSocketBoardOptions) {
  const [objects, setObjects] = useState<Record<string, BoardObject>>({});
  const [presence, setPresence] = useState<Record<string, PresenceUser>>({});
  const [cursors, setCursors] = useState<Record<string, { x: number; y: number; username: string; color: string }>>({});
  const [role, setRole] = useState<"OWNER" | "EDITOR" | "VIEWER" | "ADMIN" | "MEMBER">("EDITOR");
  const [serverRevision, setServerRevision] = useState<number>(0);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("connecting");
  const [lastError, setLastError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);
  const lastCursorSentRef = useRef<number>(0);
  const isMountedRef = useRef<boolean>(true);
  const serverRevisionRef = useRef<number>(0);

  useEffect(() => {
    serverRevisionRef.current = serverRevision;
  }, [serverRevision]);

  const sendMessage = useCallback((msg: WSMessage) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const outbound = {
        ...msg,
        client_revision: msg.client_revision ?? serverRevisionRef.current,
      };
      wsRef.current.send(JSON.stringify(outbound));
    }
  }, []);

  const sendCursor = useCallback((x: number, y: number) => {
    const now = performance.now();
    // Throttle to 30fps (~33ms) to prevent network congestion
    if (now - lastCursorSentRef.current < 33) return;
    lastCursorSentRef.current = now;

    sendMessage({
      type: "CURSOR_MOVED",
      board_id: boardId,
      payload: { x, y },
    });
  }, [boardId, sendMessage]);

  const createObject = useCallback((obj: Partial<BoardObject> & { id: string; type: any }) => {
    const operation_id = `op_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
    
    // Optimistic UI update
    const newObj: BoardObject = {
      id: obj.id,
      board_id: boardId,
      type: obj.type,
      x: obj.x ?? 100,
      y: obj.y ?? 100,
      width: obj.width ?? 160,
      height: obj.height ?? 120,
      rotation: obj.rotation ?? 0,
      z_index: obj.z_index ?? Object.keys(objects).length,
      color: obj.color ?? "#ffffff",
      fill: obj.fill ?? "#ffffff",
      stroke: obj.stroke ?? "#000000",
      stroke_width: obj.stroke_width ?? 1.5,
      text: obj.text ?? "",
      properties: obj.properties ?? {},
      version: 1,
    };
    setObjects((prev) => ({ ...prev, [newObj.id]: newObj }));

    sendMessage({
      type: "OBJECT_CREATED",
      operation_id,
      board_id: boardId,
      object_id: newObj.id,
      payload: newObj,
    });
  }, [boardId, objects, sendMessage]);

  const moveObject = useCallback((id: string, x: number, y: number) => {
    const operation_id = `op_move_${Date.now()}_${id}`;
    
    // Optimistic update
    setObjects((prev) => {
      const existing = prev[id];
      if (!existing) return prev;
      return { ...prev, [id]: { ...existing, x, y, version: existing.version + 1 } };
    });

    sendMessage({
      type: "OBJECT_MOVED",
      operation_id,
      board_id: boardId,
      object_id: id,
      payload: { id, x, y },
    });
  }, [boardId, sendMessage]);

  const resizeObject = useCallback((id: string, width: number, height: number, x?: number, y?: number) => {
    const operation_id = `op_resize_${Date.now()}_${id}`;
    
    setObjects((prev) => {
      const existing = prev[id];
      if (!existing) return prev;
      return {
        ...prev,
        [id]: {
          ...existing,
          width,
          height,
          x: x !== undefined ? x : existing.x,
          y: y !== undefined ? y : existing.y,
          version: existing.version + 1,
        },
      };
    });

    sendMessage({
      type: "OBJECT_RESIZED",
      operation_id,
      board_id: boardId,
      object_id: id,
      payload: { id, width, height, x, y },
    });
  }, [boardId, sendMessage]);

  const updateObject = useCallback((id: string, updates: Partial<BoardObject>) => {
    const operation_id = `op_update_${Date.now()}_${id}`;

    setObjects((prev) => {
      const existing = prev[id];
      if (!existing) return prev;
      return { ...prev, [id]: { ...existing, ...updates, version: existing.version + 1 } };
    });

    sendMessage({
      type: "OBJECT_UPDATED",
      operation_id,
      board_id: boardId,
      object_id: id,
      payload: { id, ...updates },
    });
  }, [boardId, sendMessage]);

  const deleteObject = useCallback((id: string) => {
    const operation_id = `op_del_${Date.now()}_${id}`;

    setObjects((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });

    sendMessage({
      type: "OBJECT_DELETED",
      operation_id,
      board_id: boardId,
      object_id: id,
    });
  }, [boardId, sendMessage]);

  const requestSync = useCallback(() => {
    sendMessage({
      type: "SYNC_REQUEST",
      board_id: boardId,
    });
  }, [boardId, sendMessage]);

  // Connect WebSocket
  useEffect(() => {
    isMountedRef.current = true;

    if (!token || !boardId) {
      setConnectionStatus("disconnected");
      return;
    }

    function connect() {
      if (!isMountedRef.current) return;
      setConnectionStatus((prev) => (prev === "connected" ? "reconnecting" : "connecting"));

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const isDev = typeof window !== "undefined" && window.location.port === "5173";
      const host = isDev ? "127.0.0.1:8080" : window.location.host;
      const wsUrl = `${protocol}//${host}/ws/boards/${boardId}?token=${token}`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isMountedRef.current) return;
        setConnectionStatus("connected");
        setLastError(null);
      };

      ws.onmessage = (event) => {
        if (!isMountedRef.current) return;
        try {
          const msg: WSMessage = JSON.parse(event.data);

          // Monotonic revision gap recovery check
          if (
            msg.server_revision &&
            serverRevisionRef.current > 0 &&
            msg.server_revision > serverRevisionRef.current + 1
          ) {
            sendMessage({
              type: "SYNC_REQUEST",
              board_id: boardId,
            });
          }

          switch (msg.type) {
            case "SYNC_SNAPSHOT": {
              const payload: BoardSnapshotPayload = msg.payload;
              const objMap: Record<string, BoardObject> = {};
              (payload.objects || []).forEach((o) => {
                objMap[o.id] = o;
              });
              setObjects(objMap);
              setRole(payload.role || "EDITOR");
              setServerRevision(payload.server_revision || 0);

              const presMap: Record<string, PresenceUser> = {};
              (payload.presence || []).forEach((p) => {
                presMap[p.user_id] = p;
              });
              setPresence(presMap);
              break;
            }

            case "USER_JOINED": {
              const u: PresenceUser = msg.payload?.user;
              if (u) {
                setPresence((prev) => ({ ...prev, [u.user_id]: u }));
              }
              break;
            }

            case "USER_LEFT": {
              const uid = msg.user_id || msg.payload?.user_id;
              if (uid) {
                setPresence((prev) => {
                  const next = { ...prev };
                  delete next[uid];
                  return next;
                });
                setCursors((prev) => {
                  const next = { ...prev };
                  delete next[uid];
                  return next;
                });
              }
              break;
            }

            case "CURSOR_MOVED": {
              const uid = msg.user_id || msg.payload?.user_id;
              if (uid && uid !== currentUser?.id) {
                setCursors((prev) => ({
                  ...prev,
                  [uid]: {
                    x: msg.payload?.x ?? 0,
                    y: msg.payload?.y ?? 0,
                    username: msg.user_name || "User",
                    color: msg.user_color || "#3B82F6",
                  },
                }));
              }
              break;
            }

            case "OBJECT_CREATED": {
              const created: BoardObject = msg.payload;
              if (created && created.id) {
                setObjects((prev) => ({ ...prev, [created.id]: created }));
                if (msg.server_revision) setServerRevision(msg.server_revision);
              }
              break;
            }

            case "OBJECT_MOVED": {
              if (msg.payload && msg.payload.id) {
                const { id, x, y, version } = msg.payload;
                setObjects((prev) => {
                  const ex = prev[id];
                  if (!ex) return prev;
                  return { ...prev, [id]: { ...ex, x, y, version: version ?? ex.version + 1 } };
                });
                if (msg.server_revision) setServerRevision(msg.server_revision);
              }
              break;
            }

            case "OBJECT_RESIZED": {
              if (msg.payload && msg.payload.id) {
                const { id, width, height, x, y, version } = msg.payload;
                setObjects((prev) => {
                  const ex = prev[id];
                  if (!ex) return prev;
                  return {
                    ...prev,
                    [id]: {
                      ...ex,
                      width,
                      height,
                      x: x !== undefined ? x : ex.x,
                      y: y !== undefined ? y : ex.y,
                      version: version ?? ex.version + 1,
                    },
                  };
                });
                if (msg.server_revision) setServerRevision(msg.server_revision);
              }
              break;
            }

            case "OBJECT_UPDATED": {
              const updated: BoardObject = msg.payload;
              if (updated && updated.id) {
                setObjects((prev) => ({ ...prev, [updated.id]: updated }));
                if (msg.server_revision) setServerRevision(msg.server_revision);
              }
              break;
            }

            case "OBJECT_DELETED": {
              const delId = msg.object_id || msg.payload?.id;
              if (delId) {
                setObjects((prev) => {
                  const next = { ...prev };
                  delete next[delId];
                  return next;
                });
                if (msg.server_revision) setServerRevision(msg.server_revision);
              }
              break;
            }

            case "ACK": {
              if (msg.server_revision) {
                setServerRevision(msg.server_revision);
              }
              break;
            }

            case "ERROR": {
              setLastError(msg.payload?.detail || "Operation error");
              sendMessage({
                type: "SYNC_REQUEST",
                board_id: boardId,
              });
              break;
            }
          }
        } catch (err) {
          console.error("Failed to parse incoming WebSocket message:", err);
        }
      };

      ws.onclose = (event: CloseEvent) => {
        if (!isMountedRef.current) return;
        if (event.code === 1008 || event.code === 4003) {
          setConnectionStatus("disconnected");
          setLastError("Access denied or session expired.");
          return;
        }
        setConnectionStatus("reconnecting");
        // Reconnect backoff
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 2000);
      };

      ws.onerror = (err) => {
        console.warn("WebSocket encountered error:", err);
      };
    }

    connect();

    return () => {
      isMountedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [boardId, token, currentUser?.id]);

  return {
    objects: Object.values(objects),
    objectsMap: objects,
    presence: Object.values(presence),
    cursors,
    role,
    serverRevision,
    connectionStatus,
    lastError,
    sendCursor,
    createObject,
    moveObject,
    resizeObject,
    updateObject,
    deleteObject,
    requestSync,
  };
}
