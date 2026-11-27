import { NextRequest } from "next/server";
import { caseApiFetch, errorResponse } from "@/lib/api/server";
export async function POST(req: NextRequest, { params }: { params: Promise<{ decisionId: string }> }) {
  try {
    const { decisionId } = await params;
    const body = await req.json().catch(() => ({}));
    return Response.json(await caseApiFetch(`/api/v1/hitl/${encodeURIComponent(decisionId)}/escalate`, {
      method: "POST",
      body: JSON.stringify(body),
      timeoutMs: 30000,
    }));
  } catch (e) { return errorResponse(e); }
}
