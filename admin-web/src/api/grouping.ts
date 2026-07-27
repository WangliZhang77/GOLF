import client from "./client";

export type GroupStatus = "scheduled" | "playing" | "completed";

export interface CompetitionGroupPlayer {
  id: number;
  group_id: number;
  member_id: number;
  registration_id: number | null;
  order_number: number;
  handicap: string | null;
  team_id: number | null;
}

export interface CompetitionGroup {
  id: number;
  competition_id: number;
  group_number: number;
  tee_time: string | null;
  starting_hole: number;
  status: GroupStatus;
  players: CompetitionGroupPlayer[];
}

export async function listGroups(competitionId: number): Promise<CompetitionGroup[]> {
  const { data } = await client.get<CompetitionGroup[]>(
    `/competitions/${competitionId}/groups`
  );
  return data;
}

export async function generateGroups(
  competitionId: number,
  payload: {
    group_size?: number;
    force?: boolean;
    first_tee_time?: string;
    interval_minutes?: number;
    starting_hole?: number;
  }
): Promise<CompetitionGroup[]> {
  const { data } = await client.post<CompetitionGroup[]>(
    `/competitions/${competitionId}/groups/generate`,
    payload
  );
  return data;
}

export async function updateGroup(
  competitionId: number,
  groupId: number,
  payload: { tee_time?: string; starting_hole?: number; status?: GroupStatus }
): Promise<CompetitionGroup> {
  const { data } = await client.put<CompetitionGroup>(
    `/competitions/${competitionId}/groups/${groupId}`,
    payload
  );
  return data;
}

export async function movePlayer(
  competitionId: number,
  playerId: number,
  targetGroupId: number
): Promise<CompetitionGroup> {
  const { data } = await client.post<CompetitionGroup>(
    `/competitions/${competitionId}/groups/players/${playerId}/move`,
    { target_group_id: targetGroupId }
  );
  return data;
}

export async function startCompetition(
  competitionId: number
): Promise<{ id: number; status: string }> {
  const { data } = await client.post<{ id: number; status: string }>(
    `/competitions/${competitionId}/start`
  );
  return data;
}

export async function getMyGroup(competitionId: number): Promise<CompetitionGroup> {
  const { data } = await client.get<CompetitionGroup>(
    `/competitions/${competitionId}/groups/my-group`
  );
  return data;
}
