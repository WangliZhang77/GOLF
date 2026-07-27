import client from "./client";

export interface CompetitionGroupPlayer {
  id: number;
  member_id: number;
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
  status: string;
  players: CompetitionGroupPlayer[];
}

export async function getMyGroup(competitionId: number): Promise<CompetitionGroup> {
  const { data } = await client.get<CompetitionGroup>(
    `/competitions/${competitionId}/groups/my-group`
  );
  return data;
}
