import { caseApiFetch, errorResponse } from "@/lib/api/server";
export async function GET(_: Request, { params }: { params: Promise<{ caseId: string }> }) {
  try {
    const { caseId } = await params;
    return Response.json(await caseApiFetch(`/api/v1/audit/${encodeURIComponent(caseId)}`));
  } catch (e) { return errorResponse(e); }
}
