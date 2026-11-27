import 'server-only';
import { getServerConfig } from '@/lib/config/server';

export type ApiError = {
  status: number;
  code: string;
  message: string;
  detail?: unknown;
};

export class CaseApiError extends Error {
  status: number;
  code: string;
  detail?: unknown;
  constructor(err: ApiError) {
    super(err.message);
    this.name = 'CaseApiError';
    this.status = err.status;
    this.code = err.code;
    this.detail = err.detail;
  }
}

function normalizeError(status: number, body: unknown): ApiError {
  const b = (body && typeof body === 'object') ? body as Record<string, unknown> : {};
  const detail = b.detail;
  const detailObj = (detail && typeof detail === 'object') ? detail as Record<string, unknown> : null;
  const message =
    (typeof detailObj?.error === 'string' && detailObj.error) ||
    (typeof detailObj?.message === 'string' && detailObj.message) ||
    (typeof b.error === 'string' && b.error) ||
    (typeof b.message === 'string' && b.message) ||
    (typeof detail === 'string' && detail) ||
    `Request failed (${status})`;
  const code =
    (typeof detailObj?.code === 'string' && detailObj.code) ||
    (typeof b.code === 'string' && b.code) ||
    (status === 401 ? 'AUTHENTICATION_REQUIRED' :
     status === 403 ? 'AUTHZ_FORBIDDEN' :
     status === 422 ? 'VALIDATION_ERROR' :
     status === 429 ? 'RATE_LIMITED' :
     status >= 500 ? 'BACKEND_ERROR' : 'REQUEST_FAILED');
  return { status, code, message, detail };
}

export async function caseApiFetch<T>(path: string, init: RequestInit & { timeoutMs?: number } = {}): Promise<T> {
  const { baseUrl, apiKey } = getServerConfig();
  const { timeoutMs = 20000, headers, ...rest } = init;
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${baseUrl}${path}`, {
      ...rest,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(apiKey ? { 'X-API-Key': apiKey } : {}),
        ...(headers || {}),
      },
      cache: 'no-store',
    });
    const text = await res.text();
    let body: unknown = null;
    try { body = text ? JSON.parse(text) : null; } catch { body = text; }
    if (!res.ok) throw new CaseApiError(normalizeError(res.status, body));
    return body as T;
  } catch (e: any) {
    if (e instanceof CaseApiError) throw e;
    if (e?.name === 'AbortError') throw new CaseApiError({ status: 504, code: 'TIMEOUT', message: 'Request timed out' });
    throw new CaseApiError({ status: 502, code: 'BACKEND_OFFLINE', message: 'Cannot reach CASE API', detail: String(e?.message || e) });
  } finally {
    clearTimeout(t);
  }
}

export function errorResponse(e: unknown) {
  const err = e instanceof CaseApiError ? e : new CaseApiError({ status: 500, code: 'INTERNAL_ERROR', message: 'Unexpected error' });
  return Response.json({ error: { status: err.status, code: err.code, message: err.message, detail: err.detail } }, { status: err.status >= 400 ? err.status : 500 });
}
