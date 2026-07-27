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

export interface RankingPreviewItem {
  scope: RankingScope;
  member_id: number | null;
  team_id: number | null;
  rank: number;
  score: string;
  award: string | null;
}

export async function previewRankings(
  competitionId: number,
  scope?: RankingScope
): Promise<RankingPreviewItem[]> {
  const { data } = await client.get<RankingPreviewItem[]>(
    `/competitions/${competitionId}/rankings/preview`,
    { params: scope ? { scope } : undefined }
  );
  return data;
}

export async function publishRankings(competitionId: number): Promise<Ranking[]> {
  const { data } = await client.post<Ranking[]>(
    `/competitions/${competitionId}/rankings/publish`
  );
  return data;
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

export async function updateRankingAward(
  competitionId: number,
  rankingId: number,
  award: string | null
): Promise<Ranking> {
  const { data } = await client.patch<Ranking>(
    `/competitions/${competitionId}/rankings/${rankingId}`,
    { award }
  );
  return data;
}
