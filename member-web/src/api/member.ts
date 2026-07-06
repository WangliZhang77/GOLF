import client from "./client";

export interface MemberProfile {
  id: number;
  user_id: number | null;
  chinese_name: string;
  english_name: string | null;
  golf_age: number | null;
  club_number: string | null;
  handicap: string | null;
  level: "honorary" | "formal" | "probationary" | "blacklist";
  status: "active" | "sleeping" | "cancelled";
  branch_id: number | null;
  team_id: number | null;
  join_date: string | null;
  nz_address: string | null;
  local_phone: string | null;
  passport_no: string | null;
  visa_type: string | null;
  payment_account: string | null;
  emergency_contact: string | null;
}

export async function getMyMember(): Promise<MemberProfile> {
  const { data } = await client.get<MemberProfile>("/members/me");
  return data;
}

export async function updateMyMember(payload: {
  english_name?: string;
  golf_age?: number;
  club_number?: string;
}): Promise<MemberProfile> {
  const { data } = await client.put<MemberProfile>("/members/me", payload);
  return data;
}
