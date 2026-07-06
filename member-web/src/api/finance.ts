import client from "./client";

export type LedgerStatus = "confirmed" | "voided" | "refunded";

export interface Bill {
  id: number;
  direction: string;
  category: string;
  amount: string;
  currency: string;
  title: string;
  remark: string | null;
  status: LedgerStatus;
  is_paid: boolean;
  created_at: string;
}

export async function getMyBills(): Promise<Bill[]> {
  const { data } = await client.get<Bill[]>("/finance/me/bills");
  return data;
}
