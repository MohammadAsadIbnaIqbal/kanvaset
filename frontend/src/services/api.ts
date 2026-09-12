import type { AuthResponse, User } from "../types/auth";
import type { Board, BoardMember, Workspace } from "../types/board";

const API_BASE = "/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export const getToken = (): string | null => {
  return localStorage.getItem("kanvaset_token");
};

export const setToken = (token: string): void => {
  localStorage.setItem("kanvaset_token", token);
};

export const removeToken = (): void => {
  localStorage.removeItem("kanvaset_token");
};

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = "Request failed";
    try {
      const data = await response.json();
      errorDetail = data.detail || errorDetail;
    } catch {
      errorDetail = response.statusText;
    }
    throw new ApiError(errorDetail, response.status);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  // Auth
  async login(email: string, password: string): Promise<AuthResponse> {
    return request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  async register(email: string, username: string, password: string): Promise<AuthResponse> {
    return request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, username, password }),
    });
  },

  async getMe(): Promise<User> {
    return request<User>("/auth/me");
  },

  // Workspaces
  async getWorkspaces(): Promise<Workspace[]> {
    return request<Workspace[]>("/workspaces");
  },

  async createWorkspace(name: string): Promise<Workspace> {
    return request<Workspace>("/workspaces", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  },

  async addWorkspaceMember(workspaceId: string, userQuery: string, role: string) {
    return request(`/workspaces/${workspaceId}/members`, {
      method: "POST",
      body: JSON.stringify({ user_email_or_username: userQuery, role }),
    });
  },

  // Boards
  async getWorkspaceBoards(workspaceId: string): Promise<Board[]> {
    return request<Board[]>(`/workspaces/${workspaceId}/boards`);
  },

  async createBoard(workspaceId: string, name: string, description?: string): Promise<Board> {
    return request<Board>(`/workspaces/${workspaceId}/boards`, {
      method: "POST",
      body: JSON.stringify({ name, description }),
    });
  },

  async getBoard(boardId: string): Promise<Board> {
    return request<Board>(`/boards/${boardId}`);
  },

  async getBoardSnapshot(boardId: string): Promise<any> {
    return request<any>(`/boards/${boardId}/snapshot`);
  },

  async updateBoard(boardId: string, updates: { name?: string; description?: string }): Promise<Board> {
    return request<Board>(`/boards/${boardId}`, {
      method: "PATCH",
      body: JSON.stringify(updates),
    });
  },

  async deleteBoard(boardId: string): Promise<void> {
    return request<void>(`/boards/${boardId}`, {
      method: "DELETE",
    });
  },

  async addBoardMember(boardId: string, userQuery: string, role: string): Promise<BoardMember> {
    return request<BoardMember>(`/boards/${boardId}/members`, {
      method: "POST",
      body: JSON.stringify({ user_email_or_username: userQuery, role }),
    });
  },

  async getBoardMembers(boardId: string): Promise<BoardMember[]> {
    return request<BoardMember[]>(`/boards/${boardId}/members`);
  },
};
