import axios from "axios";

import i18n from "../i18n";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  timeout: 10000,
});

client.interceptors.request.use((config) => {
  config.headers["Accept-Language"] = i18n.language;
  const token = localStorage.getItem("token");
  if (token) {
    config.headers["Authorization"] = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error?.response?.status === 401 && localStorage.getItem("token")) {
      localStorage.removeItem("token");
      localStorage.removeItem("refresh_token");
      window.location.href = "/";
    }
    return Promise.reject(error);
  }
);

export default client;

export async function fetchWelcome(): Promise<{ lang: string; message: string }> {
  const { data } = await client.get("/demo/welcome");
  return data;
}

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
}

export async function login(username: string, password: string) {
  const { data } = await client.post("/auth/login", { username, password });
  return data as { access_token: string; refresh_token: string; user: User };
}

export async function getMe(): Promise<User> {
  const { data } = await client.get<User>("/auth/me");
  return data;
}
