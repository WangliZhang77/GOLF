import client from "./client";

export type MemberLevel = "honorary" | "formal" | "probationary" | "blacklist";
export type MemberStatus = "active" | "sleeping" | "cancelled";

export interface Member {
  id: number;
  user_id: number | null;
  chinese_name: string;
  english_name: string | null;
  golf_age: number | null;
  club_number: string | null;
  handicap: string | null;
  level: MemberLevel;
  status: MemberStatus;
  branch_id: number | null;
  team_id: number | null;
  join_date: string | null;
  // 仅特权角色返回
  nz_address?: string | null;
  local_phone?: string | null;
  passport_no?: string | null;
}

export interface MemberCreatePayload {
  chinese_name: string;
  english_name?: string;
  golf_age?: number;
  club_number?: string;
  level?: MemberLevel;
  branch_id?: number;
  nz_address?: string;
  local_phone?: string;
  passport_no?: string;
  account_username?: string;
  account_password?: string;
}

export async function listMembers(): Promise<Member[]> {
  const { data } = await client.get<Member[]>("/members");
  return data;
}

export async function createMember(payload: MemberCreatePayload): Promise<Member> {
  const { data } = await client.post<Member>("/members", payload);
  return data;
}

export async function blacklistMember(id: number): Promise<Member> {
  const { data } = await client.post<Member>(`/members/${id}/blacklist`);
  return data;
}

export async function promoteMember(
  id: number
): Promise<{ id: number; level: MemberLevel; promoted: boolean; reason: string | null }> {
  const { data } = await client.post(`/members/${id}/promote`);
  return data;
}

export async function sleepScan(): Promise<{ marked_sleeping: number }> {
  const { data } = await client.post("/members/sleep-scan");
  return data;
}
