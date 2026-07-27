import client from "./client";

export interface Sponsor {
  id: number;
  company_name: string;
  industry: string | null;
  contact_name: string | null;
  phone: string | null;
  email: string | null;
  website: string | null;
  level: string | null;
  is_active: boolean;
}

export interface SponsorContract {
  id: number;
  sponsor_id: number;
  competition_id: number | null;
  amount: string;
  start_date: string;
  end_date: string | null;
  benefit: string | null;
}

export async function listSponsors(): Promise<Sponsor[]> {
  const { data } = await client.get<Sponsor[]>("/sponsors");
  return data;
}

export async function createSponsor(payload: {
  company_name: string;
  industry?: string;
  contact_name?: string;
  phone?: string;
  email?: string;
  website?: string;
  level?: string;
}): Promise<Sponsor> {
  const { data } = await client.post<Sponsor>("/sponsors", payload);
  return data;
}

export async function updateSponsor(
  id: number,
  payload: Partial<
    Pick<
      Sponsor,
      "company_name" | "industry" | "contact_name" | "phone" | "email" | "website" | "level" | "is_active"
    >
  >
): Promise<Sponsor> {
  const { data } = await client.put<Sponsor>(`/sponsors/${id}`, payload);
  return data;
}

export async function listContracts(sponsorId: number): Promise<SponsorContract[]> {
  const { data } = await client.get<SponsorContract[]>(`/sponsors/${sponsorId}/contracts`);
  return data;
}

export async function createContract(
  sponsorId: number,
  payload: {
    competition_id?: number;
    amount: number;
    start_date: string;
    end_date?: string;
    benefit?: string;
  }
): Promise<SponsorContract> {
  const { data } = await client.post<SponsorContract>(
    `/sponsors/${sponsorId}/contracts`,
    payload
  );
  return data;
}
