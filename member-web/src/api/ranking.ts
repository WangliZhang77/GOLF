import client from "./client";

export type RankingScope = "individual" | "team";

export interface Ranking {
  id: number;
  competition_id: number;
  scope: RankingScope;
  member_id: number | null;
  team_id: number | null;
  rank: number;
  score: string;
  award: string | null;
}

export async function listRankings(
  competitionId: number,
  scope?: RankingScope
): Promise<Ranking[]> {
  const { data } = await client.get<Ranking[]>(`/competitions/${competitionId}/rankings`, {
    params: scope ? { scope } : undefined,
  });
  return data;
}
