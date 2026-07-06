import client from "./client";

export type ActivityType =
  | "weekly_round"
  | "team_building"
  | "course_visit"
  | "networking"
  | "newbie_salon";

export interface Activity {
  id: number;
  title: string;
  description: string | null;
  activity_type: ActivityType;
  status: string;
  course_name: string | null;
  location: string | null;
  start_at: string;
  max_participants: number;
  max_family_slots: number;
  family_allowed: boolean;
  course_slots_locked: boolean;
  member_registered_count?: number;
}

export interface FamilyCompanion {
  name: string;
  relation?: string;
}

export async function listActivities(): Promise<Activity[]> {
  const { data } = await client.get<Activity[]>("/activities");
  return data;
}

export async function registerActivity(
  id: number,
  family_companions: FamilyCompanion[] = []
) {
  const { data } = await client.post(`/activities/${id}/register`, {
    family_companions,
  });
  return data;
}

export async function checkinActivity(id: number, token: string) {
  const { data } = await client.post(`/activities/${id}/checkin`, { token });
  return data;
}

/** 解析扫码内容 ACT:{id}:{token} */
export function parseCheckinQr(value: string): { id: number; token: string } | null {
  const m = value.trim().match(/^ACT:(\d+):(.+)$/);
  if (!m) return null;
  return { id: Number(m[1]), token: m[2] };
}
