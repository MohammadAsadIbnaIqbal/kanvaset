export interface User {
  id: string;
  email: string;
  username: string;
  avatar_url?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}
