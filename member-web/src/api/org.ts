import client from "./client";

export interface Team {
  id: number;
  name: string;
  branch_id: number;
}

export async function listTeams(): Promise<Team[]> {
  const { data } = await client.get<Team[]>("/org/teams");
  return data;
}
