import client from "./client";

export interface Course {
  id: number;
  name_zh: string;
  name_en: string | null;
  address: string | null;
  city: string | null;
  contact_name: string | null;
  contact_phone: string | null;
  holes: number | null;
  par: number | null;
  rating: string | null;
  slope: number | null;
  is_active: boolean;
  remark: string | null;
}

export async function listCourses(): Promise<Course[]> {
  const { data } = await client.get<Course[]>("/courses");
  return data;
}

export async function createCourse(payload: {
  name_zh: string;
  name_en?: string;
  address?: string;
  city?: string;
  contact_name?: string;
  contact_phone?: string;
  holes?: number;
  par?: number;
  rating?: number;
  slope?: number;
  remark?: string;
}): Promise<Course> {
  const { data } = await client.post<Course>("/courses", payload);
  return data;
}

export async function updateCourse(
  id: number,
  payload: Partial<
    Pick<
      Course,
      | "name_zh"
      | "name_en"
      | "address"
      | "city"
      | "contact_name"
      | "contact_phone"
      | "holes"
      | "par"
      | "rating"
      | "slope"
      | "is_active"
      | "remark"
    >
  >
): Promise<Course> {
  const { data } = await client.put<Course>(`/courses/${id}`, payload);
  return data;
}
