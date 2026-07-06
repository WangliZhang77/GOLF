import client from "./client";

export interface Organization {
  id: number;
  name: string;
  level: "headquarters" | "branch";
  parent_id: number | null;
  region: string | null;
  registration_no: string | null;
  contact_name: string | null;
  contact_phone: string | null;
  is_active: boolean;
}

export interface Team {
  id: number;
  name: string;
  branch_id: number;
  captain_id: number | null;
  home_course: string | null;
  is_active: boolean;
}

export type EnrollmentStatus =
  | "pending_captain"
  | "pending_branch"
  | "approved"
  | "rejected";

export interface Enrollment {
  id: number;
  team_id: number;
  user_id: number;
  status: EnrollmentStatus;
  remark: string | null;
}

export async function listOrganizations(): Promise<Organization[]> {
  const { data } = await client.get<Organization[]>("/org/organizations");
  return data;
}

export async function createOrganization(payload: {
  name: string;
  level: "branch";
  parent_id: number;
  region?: string;
  registration_no?: string;
  contact_name?: string;
  contact_phone?: string;
}): Promise<Organization> {
  const { data } = await client.post<Organization>("/org/organizations", payload);
  return data;
}

export async function listTeams(): Promise<Team[]> {
  const { data } = await client.get<Team[]>("/org/teams");
  return data;
}

export async function createTeam(payload: {
  name: string;
  branch_id: number;
  home_course?: string;
}): Promise<Team> {
  const { data } = await client.post<Team>("/org/teams", payload);
  return data;
}

export async function listEnrollments(): Promise<Enrollment[]> {
  const { data } = await client.get<Enrollment[]>("/org/enrollments");
  return data;
}

export async function captainReview(
  id: number,
  approve: boolean
): Promise<Enrollment> {
  const { data } = await client.post<Enrollment>(
    `/org/enrollments/${id}/captain-review`,
    { approve }
  );
  return data;
}

export async function branchReview(
  id: number,
  approve: boolean
): Promise<Enrollment> {
  const { data } = await client.post<Enrollment>(
    `/org/enrollments/${id}/branch-review`,
    { approve }
  );
  return data;
}
