import client from "./client";

export type MessageType =
  | "activity_registered"
  | "dues_reminder"
  | "activity_reminder"
  | "system"
  | "score_published";

export interface Notification {
  id: number;
  message_type: MessageType;
  title_zh: string;
  title_en: string;
  body_zh: string;
  body_en: string;
  is_read: boolean;
  created_at: string;
}

export async function listMyMessages(): Promise<Notification[]> {
  const { data } = await client.get<Notification[]>("/messages/me");
  return data;
}

export async function getUnreadCount(): Promise<number> {
  const { data } = await client.get<{ count: number }>("/messages/me/unread-count");
  return data.count;
}

export async function readMessage(id: number): Promise<Notification> {
  const { data } = await client.post<Notification>(`/messages/me/${id}/read`);
  return data;
}

export async function readAllMessages(): Promise<void> {
  await client.post("/messages/me/read-all");
}

export function localizedNotification(
  n: Notification,
  lang: string
): { title: string; body: string } {
  if (lang === "en") {
    return { title: n.title_en, body: n.body_en };
  }
  return { title: n.title_zh, body: n.body_zh };
}
