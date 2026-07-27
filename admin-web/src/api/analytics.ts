import client from "./client";

export interface MemberAnalytics {
  total: number;
  new_last_30d: number;
  active: number;
  sleeping: number;
  team_count: number;
}

export interface ActivityTrendPoint {
  month: string;
  active_member_count: number;
}

export interface ActivityAnalytics {
  total: number;
  avg_participants: number;
  most_attended: { id: number; title: string; count: number } | null;
  active_trend: ActivityTrendPoint[];
}

export interface CompetitionAnalytics {
  total: number;
  total_participants: number;
  avg_net_score: number | null;
  handicap_change: number | null;
}

export interface FinanceAnalytics {
  income: string;
  expense: string;
  profit: string;
  sponsorship_total: string;
}

export interface AnalyticsDashboard {
  members: MemberAnalytics;
  activities: ActivityAnalytics;
  competitions: CompetitionAnalytics;
  finance: FinanceAnalytics;
}

export async function getAnalyticsDashboard(): Promise<AnalyticsDashboard> {
  const { data } = await client.get<AnalyticsDashboard>("/analytics/dashboard");
  return data;
}
