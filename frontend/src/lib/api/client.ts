export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(path, { cache: "no-store" });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw data?.error || { status: res.status, code: "REQUEST_FAILED", message: "Request failed" };
  return data as T;
}
export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw data?.error || { status: res.status, code: "REQUEST_FAILED", message: "Request failed" };
  return data as T;
}
