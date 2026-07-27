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
  my_registration_status?: ApprovalStatus | null;
}

export interface CompetitionRegistration {
  id: number;
  competition_id: number;
  member_id: number;
  approval_status: ApprovalStatus;
  remark: string | null;
}

export async function listCompetitions(): Promise<Competition[]> {
  const { data } = await client.get<Competition[]>("/competitions");
  return data;
}

export async function registerCompetition(
  id: number,
  remark?: string
): Promise<CompetitionRegistration> {
  const { data } = await client.post<CompetitionRegistration>(
    `/competitions/${id}/register`,
    { remark }
  );
  return data;
}
