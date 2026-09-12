export type ObjectType =
  | "sticky_note"
  | "rectangle"
  | "circle"
  | "text"
  | "connector";

export interface BoardObject {
  id: string;
  board_id: string;
  type: ObjectType;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation?: number;
  z_index?: number;
  color?: string;
  fill?: string;
  stroke?: string;
  stroke_width?: number;
  text?: string;
  properties?: Record<string, any>;
  version: number;
  is_deleted?: boolean;
  created_by?: string;
  last_modified_by?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Board {
  id: string;
  workspace_id: string;
  name: string;
  description?: string | null;
  revision: number;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
  role: "OWNER" | "EDITOR" | "VIEWER";
  objects_count?: number;
  workspace_name?: string;
  owner_username?: string;
}

export interface Workspace {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
  role: "OWNER" | "ADMIN" | "MEMBER";
  boards_count?: number;
}

export interface BoardMember {
  id: string;
  board_id: string;
  user_id: string;
  role: "OWNER" | "EDITOR" | "VIEWER";
  username: string;
  email: string;
  avatar_url?: string | null;
  created_at: string;
}

export interface PresenceUser {
  user_id: string;
  username: string;
  color: string;
  role: string;
  avatar_url?: string;
  x?: number;
  y?: number;
  last_seen?: number;
}
