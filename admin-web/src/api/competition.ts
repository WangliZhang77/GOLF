import client from "./client";

export type CompetitionType =
  | "official"
  | "team"
  | "invitation"
  | "social"
  | "training";

export type CompetitionStatus =
  | "draft"
  | "open"
  | "closed"
  | "playing"
  | "review"
  | "completed"
  | "cancelled";

export type PaymentStatus = "unpaid" | "paid" | "waived";
export type ApprovalStatus = "pending" | "approved" | "rejected";

export interface Competition {
  id: number;
  name: string;
  description: string | null;
  competition_type: CompetitionType;
  level: string | null;
  course_id: number | null;
  branch_id: number | null;
  start_time: string;
  end_time: string | null;
  registration_deadline: string | null;
  fee: string | null;
  max_players: number;
  max_handicap: string | null;
  status: CompetitionStatus;
  registered_count?: number;
  approved_count?: number;
}

export interface CompetitionRegistration {
  id: number;
  competition_id: number;
  member_id: number;
  user_id: number;
  team_id: number | null;
  registration_time: string;
  payment_status: PaymentStatus;
  approval_status: ApprovalStatus;
  remark: string | null;
}

export async function listCompetitions(): Promise<Competition[]> {
  const { data } = await client.get<Competition[]>("/competitions");
  return data;
}

export async function createCompetition(payload: {
  name: string;
  competition_type: CompetitionType;
  start_time: string;
  description?: string;
  level?: string;
  course_id?: number;
  branch_id?: number | null;
  end_time?: string;
  registration_deadline?: string;
  fee?: number;
  max_players?: number;
  max_handicap?: number;
}): Promise<Competition> {
  const { data } = await client.post<Competition>("/competitions", payload);
  return data;
}

export async function publishCompetition(id: number): Promise<Competition> {
  const { data } = await client.post<Competition>(`/competitions/${id}/publish`);
  return data;
}

export async function listCompetitionRegistrations(
  id: number
): Promise<CompetitionRegistration[]> {
  const { data } = await client.get<CompetitionRegistration[]>(
    `/competitions/${id}/registrations`
  );
  return data;
}

export async function approveRegistration(
  competitionId: number,
  regId: number,
  approve: boolean,
  remark?: string
): Promise<CompetitionRegistration> {
  const { data } = await client.post<CompetitionRegistration>(
    `/competitions/${competitionId}/registrations/${regId}/approve`,
    { approve, remark }
  );
  return data;
}
