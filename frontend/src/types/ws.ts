import type { BoardObject, PresenceUser } from "./board";

export type WSMessageType =
  | "OBJECT_CREATED"
  | "OBJECT_MOVED"
  | "OBJECT_RESIZED"
  | "OBJECT_UPDATED"
  | "OBJECT_DELETED"
  | "TASK_CREATED"
  | "TASK_UPDATED"
  | "TASK_DELETED"
  | "TASK_COMMENT_ADDED"
  | "ACTIVITY_LOGGED"
  | "CURSOR_MOVED"
  | "USER_JOINED"
  | "USER_LEFT"
  | "PRESENCE_STATE"
  | "SYNC_REQUEST"
  | "SYNC_SNAPSHOT"
  | "ACK"
  | "ERROR";

export interface WSMessage {
  type: WSMessageType;
  board_id?: string;
  project_id?: string;
  operation_id?: string;
  object_id?: string;
  task_id?: string;
  payload?: any;
  client_revision?: number;
  server_revision?: number;
  user_id?: string;
  user_name?: string;
  user_color?: string;
  timestamp?: number;
}

export interface BoardSnapshotPayload {
  board: {
    id: string;
    workspace_id: string;
    name: string;
    description?: string;
    revision: number;
    created_by?: string;
  };
  objects: BoardObject[];
  presence: PresenceUser[];
  role: "OWNER" | "EDITOR" | "VIEWER" | "ADMIN" | "MEMBER";
  server_revision: number;
}

export interface ProjectSnapshotPayload {
  project: {
    id: string;
    name: string;
    description?: string;
  };
  tasks: any[]; // we'll define Task in project.ts
  presence: PresenceUser[];
  activities?: any[];
  role: "OWNER" | "ADMIN" | "MEMBER" | "VIEWER";
  server_revision: number;
}
