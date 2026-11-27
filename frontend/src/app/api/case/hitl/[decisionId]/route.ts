import { caseApiFetch, errorResponse } from "@/lib/api/server";
export async function GET(_: Request, { params }: { params: Promise<{ decisionId: string }> }) {
  try {
    const { decisionId } = await params;
    return Response.json(await caseApiFetch(`/api/v1/hitl/${encodeURIComponent(decisionId)}`));
  } catch (e) { return errorResponse(e); }
}
