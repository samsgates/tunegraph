import { cookies } from "next/headers";
import { redirect } from "next/navigation";

const apiUrl = process.env.TUNEGRAPH_API_URL ?? "http://localhost:8000";

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const cookieStore = await cookies();
  const token = cookieStore.get("tg_access_token")?.value;
  if (!token) redirect("/login");
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${apiUrl}${path}`, {
    ...init,
    headers,
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`TuneGraph API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}
