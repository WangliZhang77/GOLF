import client from "./client";

export type LedgerDirection = "income" | "expense";
export type LedgerStatus = "confirmed" | "voided" | "refunded";
export type IncomeCategory =
  | "annual_dues"
  | "event_registration"
  | "sponsorship"
  | "course_subsidy"
  | "donation"
  | "other";
export type ExpenseCategory =
  | "course_fee"
  | "event_supplies"
  | "referee_subsidy"
  | "trophy_prize"
  | "admin_expense"
  | "payment_fee"
  | "other";

export interface Ledger {
  id: number;
  direction: LedgerDirection;
  category: string;
  amount: string;
  currency: string;
  title: string;
  remark: string | null;
  member_id: number | null;
  branch_id: number | null;
  activity_id: number | null;
  status: LedgerStatus;
  is_paid: boolean;
  payment_method: string;
  void_reason: string | null;
  reconciled: boolean;
  refund_of_id: number | null;
  created_at: string;
}

export interface LedgerSummary {
  total_income: string;
  total_expense: string;
  net: string;
  voided_count: number;
  unreconciled_count: number;
}

export interface LedgerCreate {
  direction: LedgerDirection;
  category: string;
  amount: number;
  title: string;
  remark?: string;
  member_id?: number;
  branch_id?: number;
  is_paid?: boolean;
}

export async function listLedger(params?: {
  direction?: LedgerDirection;
  category?: string;
  member_id?: number;
  reconciled?: boolean;
}): Promise<Ledger[]> {
  const { data } = await client.get<Ledger[]>("/finance/ledger", { params });
  return data;
}

export async function createLedger(body: LedgerCreate): Promise<Ledger> {
  const { data } = await client.post<Ledger>("/finance/ledger", body);
  return data;
}

export async function voidLedger(id: number, reason: string): Promise<Ledger> {
  const { data } = await client.post<Ledger>(`/finance/ledger/${id}/void`, {
    reason,
  });
  return data;
}

export async function reconcileLedger(id: number): Promise<Ledger> {
  const { data } = await client.post<Ledger>(`/finance/ledger/${id}/reconcile`);
  return data;
}

export async function markPaid(id: number): Promise<Ledger> {
  const { data } = await client.post<Ledger>(`/finance/ledger/${id}/mark-paid`);
  return data;
}

export async function refundLedger(
  id: number,
  amount?: number,
  remark?: string
): Promise<Ledger> {
  const { data } = await client.post<Ledger>(`/finance/ledger/${id}/refund`, {
    amount,
    remark,
  });
  return data;
}

export async function getSummary(): Promise<LedgerSummary> {
  const { data } = await client.get<LedgerSummary>("/finance/ledger/summary");
  return data;
}
