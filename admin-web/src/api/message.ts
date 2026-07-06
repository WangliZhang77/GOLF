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
  read_at: string | null;
  related_member_id: number | null;
  related_activity_id: number | null;
  related_ledger_id: number | null;
  created_at: string;
}

export async function listMyMessages(unreadOnly?: boolean): Promise<Notification[]> {
  const { data } = await client.get<Notification[]>("/messages/me", {
    params: unreadOnly ? { unread_only: true } : undefined,
  });
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

export async function readAllMessages(): Promise<{ marked_read: number }> {
  const { data } = await client.post<{ marked_read: number }>("/messages/me/read-all");
  return data;
}

export async function listSentMessages(): Promise<Notification[]> {
  const { data } = await client.get<Notification[]>("/messages");
  return data;
}

export async function sendDuesReminder(body: {
  member_id?: number;
  all_outstanding?: boolean;
  branch_id?: number;
}): Promise<{ sent_count: number }> {
  const { data } = await client.post<{ sent_count: number }>(
    "/messages/dues-reminder",
    body
  );
  return data;
}

export async function sendActivityReminder(
  activityId: number
): Promise<{ sent_count: number }> {
  const { data } = await client.post<{ sent_count: number }>(
    "/messages/activity-reminder",
    { activity_id: activityId }
  );
  return data;
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
