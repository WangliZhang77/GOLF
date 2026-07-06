import client from "./client";

export type UserRole =
  | "super_admin"
  | "council_admin"
  | "team_captain"
  | "event_director"
  | "finance"
  | "member";

export interface User {
  id: number;
  username: string;
  email: string | null;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  branch_id: number | null;
  team_id: number | null;
}

interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const { data } = await client.post<LoginResponse>("/auth/login", {
    username,
    password,
  });
  return data;
}

export async function getMe(): Promise<User> {
  const { data } = await client.get<User>("/auth/me");
  return data;
}
