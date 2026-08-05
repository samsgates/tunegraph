"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

const apiUrl = process.env.TUNEGRAPH_API_URL ?? "http://localhost:8000";

export async function login(formData: FormData): Promise<void> {
  const email = String(formData.get("email") ?? "");
  const password = String(formData.get("password") ?? "");
  const organization_slug = String(formData.get("organization_slug") ?? "default");
  const response = await fetch(`${apiUrl}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, organization_slug }),
    cache: "no-store"
  });
  if (!response.ok) redirect("/login?error=invalid_credentials");
  const data = (await response.json()) as { access_token: string; refresh_token: string };
  const store = await cookies();
  store.set("tg_access_token", data.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 30 * 60
  });
  store.set("tg_refresh_token", data.refresh_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    path: "/",
    maxAge: 7 * 24 * 60 * 60
  });
  redirect("/");
}

export async function logout(): Promise<void> {
  const store = await cookies();
  store.delete("tg_access_token");
  store.delete("tg_refresh_token");
  redirect("/login");
}
