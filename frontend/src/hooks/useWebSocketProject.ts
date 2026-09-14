import { useCallback, useEffect, useRef, useState } from "react";
import type { User } from "../types/auth";
import type { PresenceUser } from "../types/board";
import type { Task, Activity } from "../types/project";
import type { ProjectSnapshotPayload, WSMessage } from "../types/ws";

export type ConnectionStatus = "connecting" | "connected" | "disconnected" | "reconnecting";

interface UseWebSocketProjectOptions {
  projectId: string;
  token: string | null;
  currentUser: User | null;
}

export function useWebSocketProject({ projectId, token, currentUser }: UseWebSocketProjectOptions) {
  const [tasks, setTasks] = useState<Record<string, Task>>({});
  const [activities, setActivities] = useState<Activity[]>([]);
  const [presence, setPresence] = useState<Record<string, PresenceUser>>({});
  const [role, setRole] = useState<"OWNER" | "ADMIN" | "MEMBER" | "VIEWER">("VIEWER");
  const [serverRevision, setServerRevision] = useState<number>(0);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("connecting");
  const [lastError, setLastError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);
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

  const createTask = useCallback((task: Partial<Task> & { id: string }) => {
    const operation_id = `op_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
    
    const newTask: Task = {
      id: task.id,
      project_id: projectId,
      title: task.title || "New Task",
      description: task.description || "",
      status: task.status || "TODO",
      priority: task.priority || "MEDIUM",
      assignee_id: task.assignee_id,
      tags: task.tags || [],
      version: 1,
      is_deleted: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    setTasks((prev) => ({ ...prev, [newTask.id]: newTask }));

    sendMessage({
      type: "TASK_CREATED",
      operation_id,
      project_id: projectId,
      task_id: newTask.id,
      payload: newTask,
    });
  }, [projectId, sendMessage]);

  const updateTask = useCallback((id: string, updates: Partial<Task>) => {
    const operation_id = `op_update_${Date.now()}_${id}`;

    setTasks((prev) => {
      const existing = prev[id];
      if (!existing) return prev;
      return { ...prev, [id]: { ...existing, ...updates, version: existing.version + 1 } };
    });

    sendMessage({
      type: "TASK_UPDATED",
      operation_id,
      project_id: projectId,
      task_id: id,
      payload: { id, ...updates },
    });
  }, [projectId, sendMessage]);

  const deleteTask = useCallback((id: string) => {
    const operation_id = `op_del_${Date.now()}_${id}`;

    setTasks((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });

    sendMessage({
      type: "TASK_DELETED",
      operation_id,
      project_id: projectId,
      task_id: id,
    });
  }, [projectId, sendMessage]);

  const requestSync = useCallback(() => {
    sendMessage({
      type: "SYNC_REQUEST",
      project_id: projectId,
    });
  }, [projectId, sendMessage]);

  useEffect(() => {
    isMountedRef.current = true;

    if (!token || !projectId) {
      setConnectionStatus("disconnected");
      return;
    }

    function connect() {
      if (!isMountedRef.current) return;
      setConnectionStatus((prev) => (prev === "connected" ? "reconnecting" : "connecting"));

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const isDev = typeof window !== "undefined" && window.location.port === "5173";
      const host = isDev ? "127.0.0.1:8080" : window.location.host;
      const wsUrl = `${protocol}//${host}/ws/projects/${projectId}?token=${token}`;

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

          if (
            msg.server_revision &&
            serverRevisionRef.current > 0 &&
            msg.server_revision > serverRevisionRef.current + 1
          ) {
            sendMessage({
              type: "SYNC_REQUEST",
              project_id: projectId,
            });
          }

          switch (msg.type) {
            case "SYNC_SNAPSHOT": {
              const payload = msg.payload as ProjectSnapshotPayload;
              const objMap: Record<string, Task> = {};
              (payload.tasks || []).forEach((o: Task) => {
                objMap[o.id] = o;
              });
              setTasks(objMap);
              setActivities(payload.activities || []);
              setRole(payload.role || "VIEWER");
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
              }
              break;
            }

            case "TASK_CREATED": {
              const created: Task = msg.payload;
              if (created && created.id) {
                setTasks((prev) => ({ ...prev, [created.id]: created }));
                if (msg.server_revision) setServerRevision(msg.server_revision);
              }
              break;
            }

            case "TASK_UPDATED": {
              const updated: Task = msg.payload;
              if (updated && updated.id) {
                setTasks((prev) => ({ ...prev, [updated.id]: updated }));
                if (msg.server_revision) setServerRevision(msg.server_revision);
              }
              break;
            }

            case "TASK_DELETED": {
              const delId = msg.task_id || msg.payload?.id;
              if (delId) {
                setTasks((prev) => {
                  const next = { ...prev };
                  delete next[delId];
                  return next;
                });
                if (msg.server_revision) setServerRevision(msg.server_revision);
              }
              break;
            }

            case "ACTIVITY_LOGGED": {
              if (msg.payload) {
                 setActivities((prev) => [msg.payload, ...prev]);
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
                project_id: projectId,
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
  }, [projectId, token, currentUser?.id]);

  return {
    tasks: Object.values(tasks),
    activities,
    presence: Object.values(presence),
    role,
    serverRevision,
    connectionStatus,
    lastError,
    createTask,
    updateTask,
    deleteTask,
    requestSync,
  };
}
