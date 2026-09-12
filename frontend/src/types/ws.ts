import type { BoardObject, PresenceUser } from "./board";

export type WSMessageType =
  | "OBJECT_CREATED"
  | "OBJECT_MOVED"
  | "OBJECT_RESIZED"
  | "OBJECT_UPDATED"
  | "OBJECT_DELETED"
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
  board_id: string;
  operation_id?: string;
  object_id?: string;
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
  role: "OWNER" | "EDITOR" | "VIEWER";
  server_revision: number;
}
