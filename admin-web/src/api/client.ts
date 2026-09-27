import axios from "axios";

import i18n from "../i18n";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  timeout: 10000,
});

// 统一注入语言头，配合后端双语返回
client.interceptors.request.use((config) => {
  config.headers["Accept-Language"] = i18n.language;
  const token = localStorage.getItem("token");
  if (token) {
    config.headers["Authorization"] = `Bearer ${token}`;
  }
  return config;
});

// 统一处理 401：清除登录态并跳转登录页
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
