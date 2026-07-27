import client from "./client";

export type HandicapSource = "manual" | "competition" | "nz_golf_api";

export interface HandicapHistoryEntry {
  id: number;
  member_id: number;
  date: string;
  old_handicap: string | null;
  new_handicap: string;
  source: HandicapSource;
  competition_id: number | null;
  remark: string | null;
}

export interface HandicapDashboard {
  member_id: number;
  current_handicap: string | null;
  trend: "declining" | "rising" | "stable";
  history: HandicapHistoryEntry[];
}

export async function getMyHandicap(): Promise<HandicapDashboard> {
  const { data } = await client.get<HandicapDashboard>("/handicap/me");
  return data;
}
