import client from "./client";

export type ScoreCardStatus = "draft" | "submitted" | "checking" | "approved" | "rejected";

export interface ScoreCard {
  id: number;
  competition_id: number;
  member_id: number;
  group_id: number;
  hole1: number | null;
  hole2: number | null;
  hole3: number | null;
  hole4: number | null;
  hole5: number | null;
  hole6: number | null;
  hole7: number | null;
  hole8: number | null;
  hole9: number | null;
  hole10: number | null;
  hole11: number | null;
  hole12: number | null;
  hole13: number | null;
  hole14: number | null;
  hole15: number | null;
  hole16: number | null;
  hole17: number | null;
  hole18: number | null;
  out_score: number | null;
  in_score: number | null;
  total_score: number | null;
  handicap_snapshot: string | null;
  net_score: string | null;
  status: ScoreCardStatus;
}

export async function listScorecards(competitionId: number): Promise<ScoreCard[]> {
  const { data } = await client.get<ScoreCard[]>(
    `/competitions/${competitionId}/scorecards`
  );
  return data;
}

export async function adminReview(
  competitionId: number,
  cardId: number,
  approve: boolean,
  comment?: string
): Promise<ScoreCard> {
  const { data } = await client.post<ScoreCard>(
    `/competitions/${competitionId}/scorecards/${cardId}/admin-review`,
    { approve, comment }
  );
  return data;
}

export async function closePlay(
  competitionId: number
): Promise<{ id: number; status: string }> {
  const { data } = await client.post<{ id: number; status: string }>(
    `/competitions/${competitionId}/close-play`
  );
  return data;
}
