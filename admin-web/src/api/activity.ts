import client from "./client";

export type ActivityType =
  | "weekly_round"
  | "team_building"
  | "course_visit"
  | "networking"
  | "newbie_salon";

export type ActivityStatus = "draft" | "published" | "closed" | "cancelled";

export interface Activity {
  id: number;
  title: string;
  description: string | null;
  activity_type: ActivityType;
  status: ActivityStatus;
  branch_id: number;
  team_id: number | null;
  location: string | null;
  course_name: string | null;
  start_at: string;
  end_at: string | null;
  max_participants: number;
  max_family_slots: number;
  family_allowed: boolean;
  course_slots_locked: boolean;
  checkin_token: string;
  simple_scoring_enabled: boolean;
  member_registered_count?: number;
  family_registered_count?: number;
  checked_in_count?: number;
}

export type RegistrantType = "member" | "family";
export type RegistrationStatus =
  | "registered"
  | "checked_in"
  | "absent"
  | "cancelled";

export interface Registration {
  id: number;
  activity_id: number;
  member_id: number;
  user_id: number;
  registrant_type: RegistrantType;
  family_name: string | null;
  family_relation: string | null;
  status: RegistrationStatus;
  checked_in_at: string | null;
}

export interface AttendanceStats {
  activity_id: number;
  member_registered: number;
  family_registered: number;
  member_checked_in: number;
  family_checked_in: number;
  member_absent: number;
  attendance_rate: number;
}

export async function listActivities(): Promise<Activity[]> {
  const { data } = await client.get<Activity[]>("/activities");
  return data;
}

export async function createActivity(payload: {
  title: string;
  activity_type: ActivityType;
  branch_id: number;
  start_at: string;
  description?: string;
  course_name?: string;
  max_participants?: number;
  max_family_slots?: number;
  family_allowed?: boolean;
  course_slots_locked?: boolean;
}): Promise<Activity> {
  const { data } = await client.post<Activity>("/activities", payload);
  return data;
}

export async function publishActivity(id: number): Promise<Activity> {
  const { data } = await client.post<Activity>(`/activities/${id}/publish`);
  return data;
}

export async function listRegistrations(id: number): Promise<Registration[]> {
  const { data } = await client.get<Registration[]>(
    `/activities/${id}/registrations`
  );
  return data;
}

export async function getAttendanceStats(id: number): Promise<AttendanceStats> {
  const { data } = await client.get<AttendanceStats>(
    `/activities/${id}/attendance-stats`
  );
  return data;
}

export async function markAbsent(
  activityId: number,
  regId: number
): Promise<Registration> {
  const { data } = await client.post<Registration>(
    `/activities/${activityId}/registrations/${regId}/mark-absent`
  );
  return data;
}
